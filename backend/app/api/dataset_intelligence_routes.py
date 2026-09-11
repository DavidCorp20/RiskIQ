from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException

from app.analytics.npl import NPLAnalyticsService
from app.analytics.portfolio_intelligence import PortfolioIntelligenceService
from app.analytics.risk_analytics import RiskAnalyticsService
from app.analytics.snapshot_engine import SnapshotEngine
from app.analytics.vintage_rollrate import VintageRollRateService
from app.analytics.decision_engine import DecisionEngineService
from app.data.persistence import PortfolioPersistenceService
from app.decision.workspace import DecisionWorkspaceService

router = APIRouter(prefix="/v1/datasets", tags=["dataset-intelligence"])
persistence = PortfolioPersistenceService()
intelligence = PortfolioIntelligenceService()
risk_analytics = RiskAnalyticsService()
decision_engine = DecisionEngineService()
snapshot_engine = SnapshotEngine()
vintage = VintageRollRateService()
npl = NPLAnalyticsService()
workspace = DecisionWorkspaceService()


def _require_dataset(dataset_id: str) -> dict[str, Any]:
    rows = persistence.datasets.find({"dataset_id": dataset_id}, limit=1)
    if not rows:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return rows[0]


def _advanced_analytics(risk: dict[str, Any], vintage_analysis: dict[str, Any], current: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    par = risk.get("par") or {}
    concentration = risk.get("concentration") or {}
    segments = concentration.get("segments") or []
    products = concentration.get("products") or []
    stress = []
    base_exposure = float(risk.get("exposure") or 0)
    base_par30_balance = float((par.get("par30") or {}).get("balance") or 0)
    for shock in (0.10, 0.20, 0.30):
        stressed_balance = base_par30_balance * (1 + shock)
        stress.append({
            "shock_pct": shock,
            "additional_at_risk": round(base_par30_balance * shock, 2),
            "stressed_par30": round(stressed_balance / base_exposure, 4) if base_exposure else 0,
        })

    migration = None
    if previous:
        prev_par30 = float(previous.get("par30") or 0)
        current_par30 = float((par.get("par30") or {}).get("ratio") or 0)
        migration = {
            "available": True,
            "previous_par30": prev_par30,
            "current_par30": current_par30,
            "delta_par30": round(current_par30 - prev_par30, 4),
            "direction": "deteriorating" if current_par30 > prev_par30 else "improving" if current_par30 < prev_par30 else "stable",
        }
    else:
        migration = {"available": False, "reason": "Se requiere al menos un corte histórico anterior."}

    return {
        "risk_profile": [
            {"metric": key.upper(), "ratio": float((value or {}).get("ratio") or 0), "balance": float((value or {}).get("balance") or 0), "loans": int((value or {}).get("loans") or 0)}
            for key, value in par.items()
        ],
        "concentration": {
            "top_segments": segments[:8],
            "top_products": products[:8],
            "segment_concentration_ratio": round(sum(float(x.get("share_of_exposure") or 0) for x in segments[:3]), 4),
        },
        "migration": migration,
        "cohorts": risk.get("vintage") or vintage_analysis or [],
        "stress": stress,
        "methodology": {
            "deterministic": True,
            "stress_is_hypothetical": True,
            "migration_requires_history": True,
            "cohorts_use_origination_date_when_available": True,
            "causality_inferred": False,
        },
    }


@router.post("/{dataset_id}/run")
def run_dataset_workspace(dataset_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run the complete deterministic data-to-decision flow for one persisted dataset."""
    metadata = _require_dataset(dataset_id)
    records = persistence.portfolio_records.find({"dataset_id": dataset_id}, limit=100000)
    portfolio = {
        "customers": persistence.customers.find({"dataset_id": dataset_id}, limit=100000),
        "loans": persistence.loans.find({"dataset_id": dataset_id}, limit=100000),
        "installments": persistence.installments.find({"dataset_id": dataset_id}, limit=100000),
        "payments": persistence.payments.find({"dataset_id": dataset_id}, limit=100000),
    }
    if not portfolio["loans"]:
        raise HTTPException(status_code=422, detail="Dataset has no canonical loans to analyze")

    body = payload or {}
    as_of = str(body.get("snapshot_date") or date.today().isoformat())
    current = snapshot_engine.build(
        loans=portfolio["loans"],
        installments=portfolio["installments"],
        snapshot_date=as_of,
        business_id=dataset_id,
    )
    analysis = intelligence.analyze(records)
    risk = risk_analytics.analyze(records)
    vintage_analysis = vintage.analyze(records)
    npl_analysis = npl.analyze(records)
    decisions = decision_engine.build(risk, npl_analysis)

    snapshots = persistence.snapshots.find({"dataset_id": dataset_id}, limit=500)
    previous_candidates = [row for row in snapshots if str(row.get("snapshot_date") or "") < as_of]
    previous = max(previous_candidates, key=lambda row: str(row.get("snapshot_date") or ""), default=None)
    workspace_previous = previous or current

    result = workspace.run({
        "current": current,
        "previous": workspace_previous,
        "current_analysis": analysis,
        "history_entries": snapshots,
        "custom_rules": list(body.get("custom_rules") or []),
    })

    existing = persistence.snapshots.find(
        {"dataset_id": dataset_id, "snapshot_date": as_of},
        limit=1,
    )
    snapshot_id = existing[0].get("id") if existing else persistence.snapshots.insert({**current, "dataset_id": dataset_id})

    advanced = _advanced_analytics(risk, vintage_analysis, current, previous)
    return {
        "status": result.get("status", "healthy"),
        "contract_version": "dataset-intelligence-v4",
        "dataset": metadata,
        "dataset_id": dataset_id,
        "snapshot": {"id": snapshot_id, **current},
        "previous_snapshot": previous,
        "analysis": analysis,
        "risk_analytics": {"deterministic": risk, "npl": npl_analysis},
        "advanced_analytics": advanced,
        "decision_engine": decisions,
        "vintage": vintage_analysis,
        "workspace": result,
        "governance": {
            "real_dataset": True,
            "analytics_are_deterministic": True,
            "decision_engine_is_deterministic": True,
            "customer_actions_executed": False,
            "human_review_required": True,
            "trend_available": previous is not None,
            "roll_rate_requires_historical_snapshots": True,
            "causality_inferred": False,
            "npl_is_regulatory_definition": False,
        },
    }
