from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException

from app.analytics.portfolio_intelligence import PortfolioIntelligenceService
from app.analytics.snapshot_engine import SnapshotEngine
from app.data.persistence import PortfolioPersistenceService
from app.decision.workspace import DecisionWorkspaceService

router = APIRouter(prefix="/v1/datasets", tags=["dataset-intelligence"])
persistence = PortfolioPersistenceService()
intelligence = PortfolioIntelligenceService()
snapshot_engine = SnapshotEngine()
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

    as_of = str((payload or {}).get("snapshot_date") or date.today().isoformat())
    current = snapshot_engine.build(
        loans=portfolio["loans"],
        installments=portfolio["installments"],
        snapshot_date=as_of,
        business_id=dataset_id,
    )
    analysis = intelligence.analyze(records)

    custom_rules = list((payload or {}).get("custom_rules") or [])
    result = workspace.run({
        "current": current,
        "previous": current,
        "current_analysis": analysis,
        "custom_rules": custom_rules,
    })

    return {
        "dataset": metadata,
        "dataset_id": dataset_id,
        "snapshot": current,
        "analysis": analysis,
        "workspace": result,
        "governance": result.get("governance", {}),
    }
