from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException

from app.analytics.npl import NPLAnalyticsService
from app.analytics.portfolio_intelligence import PortfolioIntelligenceService
from app.analytics.risk_analytics import RiskAnalyticsService
from app.analytics.snapshot_engine import SnapshotEngine
from app.analytics.vintage_rollrate import VintageRollRateService
from app.data.persistence import PortfolioPersistenceService
from app.decision.workspace import DecisionWorkspaceService

router = APIRouter(prefix="/v1/datasets", tags=["dataset-intelligence"])
persistence = PortfolioPersistenceService()
intelligence = PortfolioIntelligenceService()
risk_analytics = RiskAnalyticsService()
snapshot_engine = SnapshotEngine()
vintage = VintageRollRateService()
npl = NPLAnalyticsService()
workspace = DecisionWorkspaceService()


def _require_dataset(dataset_id: str) -> dict[str, Any]:
    rows = persistence.datasets.find({"dataset_id": dataset_id}, limit=1)
    if not rows:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return rows[0]


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

    snapshots = persistence.snapshots.find({"dataset_id": dataset_id}, limit=500)
    previous_candidates = [row for row in snapshots if str(row.get("snapshot_date") or "") < as_of]
    previous = max(previous_candidates, key=lambda row: str(row.get("snapshot_date") or ""), default=None)
    workspace_previous = previous or current

    result = workspace.run({
        "current": current,
        "previous": workspace_previous,
        "current_analysis": analysis,
        "custom_rules": list(body.get("custom_rules") or []),
    })

    existing = persistence.snapshots.find(
        {"dataset_id": dataset_id, "snapshot_date": as_of},
        limit=1,
    )
    snapshot_id = existing[0].get("id") if existing else persistence.snapshots.insert({**current, "dataset_id": dataset_id})

    return {
        "status": result.get("status", "healthy"),
        "contract_version": "dataset-intelligence-v4",
        "dataset": metadata,
        "dataset_id": dataset_id,
        "snapshot": {"id": snapshot_id, **current},
        "previous_snapshot": previous,
        "analysis": analysis,
        "risk_analytics": {"deterministic": risk, "npl": npl_analysis},
        "vintage": vintage_analysis,
        "workspace": result,
        "governance": {
            "real_dataset": True,
            "analytics_are_deterministic": True,
            "customer_actions_executed": False,
            "trend_available": previous is not None,
            "roll_rate_requires_historical_snapshots": True,
            "causality_inferred": False,
            "npl_is_regulatory_definition": False,
        },
    }
