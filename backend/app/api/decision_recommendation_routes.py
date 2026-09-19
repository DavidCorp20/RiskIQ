from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.analytics.ews_engine import EWSEngine
from app.analytics.portfolio_ews import PortfolioEWSService
from app.data.persistence import PortfolioPersistenceService
from app.integrations.freshservice import compliance_service
from app.decision.decision_recommendations import (
    DecisionRecommendationEngine,
    DecisionRecommendationRepository,
)

router = APIRouter(prefix="/v1/decisions", tags=["decision-recommendations"])

ews_service = PortfolioEWSService(EWSEngine())
persistence = PortfolioPersistenceService()
recommendation_engine = DecisionRecommendationEngine()
repository = DecisionRecommendationRepository()


def _rows(payload: dict) -> tuple[list[dict], str]:
    dataset_id = str(payload.get("dataset_id") or "").strip()
    rows = payload.get("rows") or []
    if not rows and dataset_id:
        rows = persistence.portfolio_records.find(
            {"dataset_id": dataset_id},
            limit=100000,
        )
    if not dataset_id:
        raise HTTPException(status_code=422, detail="dataset_id is required")
    if not isinstance(rows, list) or not rows:
        raise HTTPException(
            status_code=422,
            detail="rows or a dataset_id with portfolio observations is required",
        )
    return rows, dataset_id


@router.post("/recommend")
def recommend_decisions(payload: dict) -> dict:
    rows, dataset_id = _rows(payload)

    try:
        ews_summary = ews_service.summarize(
            rows,
            high_score=float(payload.get("high_score", 50.0)),
        )
        recommendations = recommendation_engine.recommend(
            dataset_id=dataset_id,
            ews_summary=ews_summary,
            policy_id=str(
                payload.get("policy_id")
                or recommendation_engine.POLICY_ID
            ),
            policy_version=int(
                payload.get("policy_version")
                or recommendation_engine.POLICY_VERSION
            ),
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Persist after generation. The engine returns dictionaries to keep the
    # execution contract serializable; repository accepts the canonical model.
    from app.decision.decision_recommendations import DecisionRecommendation
    persisted = []
    for item in recommendations:
        model = DecisionRecommendation(
            recommendation_id=item["recommendation_id"],
            dataset_id=item["dataset_id"],
            loan_id=item.get("loan_id"),
            action=item["action"],
            action_level=item["action_level"],
            status=item["status"],
            requires_human_approval=bool(item["requires_human_approval"]),
            policy_id=item["policy_id"],
            policy_version=int(item["policy_version"]),
            trigger_codes=tuple(item.get("trigger_codes") or []),
            evidence=dict(item.get("evidence") or {}),
            rationale=str(item.get("rationale") or ""),
            source=str(item.get("source") or "deterministic_ews"),
            created_at=str(item.get("created_at") or ""),
            expires_at=item.get("expires_at"),
        )
        persisted.append(repository.save(model))

    return {
        "status": "proposed",
        "dataset_id": dataset_id,
        "policy": {
            "id": str(payload.get("policy_id") or recommendation_engine.POLICY_ID),
            "version": int(payload.get("policy_version") or recommendation_engine.POLICY_VERSION),
        },
        "ews": ews_summary,
        "count": len(persisted),
        "recommendations": persisted,
        "guardrails": {
            "deterministic": True,
            "ai_executes_actions": False,
            "human_approval_required_for_medium_high": True,
            "customer_actions_executed": False,
            "evidence_snapshotted": True,
            "ledger_immutable": True,
        },
    }


def _queue_compliance_review(
    item: dict,
    status: str,
    actor: str,
    justification: str,
    background_tasks: BackgroundTasks,
) -> dict:
    """Bridge review transitions into the durable compliance outbox.

    The decision ledger is authoritative. Any Freshservice/outbox failure is
    captured and reported without rolling back the approved/rejected state.
    """
    event = {
        "decision_id": item.get("recommendation_id"),
        "dataset_id": item.get("dataset_id"),
        "status": status,
        "review_state": status,
        "actor": actor,
        "justification": justification,
        "evidence_hash": item.get("evidence_hash"),
        "evidence": item.get("evidence") or {},
        "policy_id": item.get("policy_id"),
        "policy_version": item.get("policy_version"),
        "action": item.get("action"),
        "action_level": item.get("action_level"),
        "critical": str(item.get("action_level") or "").lower() in {"medium", "high"},
    }
    try:
        outbox_item = compliance_service.enqueue(
            event_type="decision_review_transition",
            event=event,
            critical=bool(event["critical"]),
        )
        background_tasks.add_task(compliance_service.process_pending, 20)
        return {
            "queued": True,
            "status": outbox_item.get("status", "pending"),
            "event_key": outbox_item.get("event_key"),
        }
    except Exception as exc:
        return {
            "queued": False,
            "status": "deferred",
            "error": str(exc)[:500],
        }


@router.post("/{recommendation_id}/approve")
def approve_decision(recommendation_id: str, payload: dict, background_tasks: BackgroundTasks) -> dict:
    actor = str(payload.get("actor") or "user").strip() or "user"
    comment = str(payload.get("comment") or payload.get("justification") or "").strip()
    if not comment:
        raise HTTPException(status_code=422, detail="comment or justification is required")
    try:
        item = repository.transition(
            recommendation_id,
            status="approved",
            actor=actor,
            comment=comment,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="recommendation not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    compliance_sync = _queue_compliance_review(item, "approved", actor, comment, background_tasks)
    return {"status": "approved", "item": item, "compliance": compliance_sync, "customer_action_executed": False}


@router.post("/{recommendation_id}/reject")
def reject_decision(recommendation_id: str, payload: dict, background_tasks: BackgroundTasks) -> dict:
    actor = str(payload.get("actor") or "user").strip() or "user"
    comment = str(payload.get("comment") or payload.get("justification") or "").strip()
    if not comment:
        raise HTTPException(status_code=422, detail="comment or justification is required")
    try:
        item = repository.transition(
            recommendation_id,
            status="rejected",
            actor=actor,
            comment=comment,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="recommendation not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    compliance_sync = _queue_compliance_review(item, "rejected", actor, comment, background_tasks)
    return {"status": "rejected", "item": item, "compliance": compliance_sync, "customer_action_executed": False}


@router.get("")
def list_decisions(
    dataset_id: str | None = Query(default=None, min_length=1, max_length=128),
    status: str | None = Query(default=None, min_length=1, max_length=64),
    action_level: str | None = Query(default=None, min_length=1, max_length=32),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    """List recommendations safely; an empty dataset is a valid 200 response."""
    try:
        items = repository.list(
            dataset_id=dataset_id.strip() if dataset_id else None,
            status=status.strip() if status else None,
            action_level=action_level.strip() if action_level else None,
            limit=limit,
        )
    except Exception:
        return {
            "count": 0,
            "items": [],
            "degraded": True,
            "error": "decision_repository_unavailable",
        }
    return {"count": len(items), "items": items, "degraded": False}


@router.get("/ledger")
def list_decision_ledger(
    dataset_id: str | None = None,
    recommendation_id: str | None = None,
    limit: int = 100,
) -> dict:
    items = repository.ledger_entries(
        dataset_id=dataset_id,
        recommendation_id=recommendation_id,
        limit=limit,
    )
    return {"count": len(items), "items": items, "immutable": True}
