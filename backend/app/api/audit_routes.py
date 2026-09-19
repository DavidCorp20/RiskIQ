from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, status

from app.audit.decision_history import DecisionHistoryService
from app.audit.reconciliation import ReconciliationAuditService
from app.integrations.freshservice import compliance_service

router = APIRouter(prefix="/v1/audit", tags=["audit"])
service = DecisionHistoryService()
reconciliation_service = ReconciliationAuditService()


@router.post("/decisions")
def record_decision(payload: dict, background_tasks: BackgroundTasks) -> dict:
    decision = payload.get("decision", payload)
    actor = str(payload.get("actor", "system"))
    recorded = service.record(decision, actor)
    critical = bool(decision.get("critical", True))
    compliance_service.enqueue(
        event_type="decision_execution",
        event={
            "decision_id": recorded.get("decision_id"),
            "status": recorded.get("status") or decision.get("status") or "executed",
            "actor": recorded.get("actor") or actor,
            "policy_id": recorded.get("policy_id"),
            "policy_version": recorded.get("policy_version"),
            "recommendation": recorded.get("recommendation"),
            "evidence": recorded.get("evidence") or {},
            "critical": critical,
        },
        critical=critical,
    )
    background_tasks.add_task(compliance_service.process_pending, 20)
    return recorded


@router.get("/decisions")
def list_decisions(status: str | None = None, dataset_id: str | None = None) -> dict:
    entries = service.list(status=status, dataset_id=dataset_id)
    return {"count": len(entries), "entries": entries}


@router.post("/decisions/{decision_id}/outcome")
def resolve_decision(decision_id: str, payload: dict) -> dict:
    try:
        return service.resolve(decision_id, payload.get("outcome", payload))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Decision not found") from exc


@router.get("/freshservice/status")
def freshservice_status() -> dict:
    compliance_service._ensure_indexes()
    pending = compliance_service.outbox.find({"status": {"$in": ["pending", "retry"]}}, limit=1000)
    sent = compliance_service.outbox.find({"status": "sent"}, limit=1000)
    return {"enabled": compliance_service.client.enabled, "pending": len(pending), "sent": len(sent), "integration": "freshservice"}


@router.post("/freshservice/sync")
async def freshservice_sync(limit: int = 20) -> dict:
    return await compliance_service.process_pending(max(1, min(limit, 100)))


@router.get("/reconciliation")
def list_reconciliation_audit(dataset_id: str | None = None, limit: int = 500) -> dict:
    entries = reconciliation_service.list(dataset_id=dataset_id, limit=max(1, min(limit, 1000)))
    return {"count": len(entries), "entries": entries}


@router.post("/freshservice/webhook", status_code=status.HTTP_202_ACCEPTED)
def freshservice_webhook(
    payload: dict,
    x_riskiq_webhook_secret: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> dict:
    provided_secret = x_riskiq_webhook_secret
    if not provided_secret and authorization and authorization.lower().startswith("bearer "):
        provided_secret = authorization[7:].strip()

    if not compliance_service.verify_webhook_secret(provided_secret):
        raise HTTPException(status_code=401, detail="Invalid Freshservice webhook credentials")

    try:
        return compliance_service.process_webhook(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
