from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.analytics.risk_analytics import RiskAnalyticsService
from app.data.persistence import PortfolioPersistenceService
from app.simulation.scenario_simulator import ScenarioSimulator

router = APIRouter(prefix="/v1/simulator", tags=["simulator"])
service = ScenarioSimulator()
risk_analytics = RiskAnalyticsService()
persistence = PortfolioPersistenceService()


def _require_dataset(dataset_id: str) -> dict:
    rows = persistence.datasets.find({"dataset_id": dataset_id}, limit=1)
    if not rows:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return rows[0]


def _latest_snapshot(dataset_id: str) -> dict:
    rows = persistence.snapshots.find({"dataset_id": dataset_id}, limit=500)
    if not rows:
        raise HTTPException(status_code=409, detail="Run the selected dataset before using the simulator")
    return max(rows, key=lambda row: str(row.get("snapshot_date") or ""))


@router.post("/run")
def run_scenario(payload: dict) -> dict:
    """Run a sensitivity scenario from the same current point-in-time source used by Risk Analytics."""
    dataset_id = str(payload.get("dataset_id") or "").strip()
    if dataset_id:
        _require_dataset(dataset_id)
        records_repo = getattr(persistence, "portfolio_records", None)
        records = records_repo.find({"dataset_id": dataset_id}, limit=100000) if records_repo is not None else []

        if records:
            risk = risk_analytics.analyze(records)
            if not risk.get("available"):
                raise HTTPException(status_code=409, detail="No active canonical portfolio is available for stress testing")
            portfolio = {"balance": risk.get("exposure", 0), "par30": float(risk.get("par", {}).get("par30", {}).get("ratio", 0) or 0), "par90": float(risk.get("par", {}).get("par90", {}).get("ratio", 0) or 0)}
            baseline_source = "canonical_portfolio_risk_analytics"
            snapshot_date = risk.get("snapshot")
        else:
            snapshot = _latest_snapshot(dataset_id)
            portfolio = {"balance": snapshot.get("outstanding_balance", 0), "par30": snapshot.get("par30", 0), "par90": snapshot.get("par90", 0)}
            baseline_source = "persisted_snapshot"
            snapshot_date = snapshot.get("snapshot_date")

        changes = dict(payload.get("changes") or {})
        if "par_shock_points" not in changes and "shock_pct" in payload:
            changes["par_shock_points"] = payload.get("shock_pct")
        result = service.simulate(portfolio, changes, payload.get("name") or payload.get("scenario_name") or "Custom scenario")
        result["dataset_id"] = dataset_id
        result["baseline_source"] = baseline_source
        result["snapshot_date"] = snapshot_date
        return result

    portfolio = payload.get("portfolio", {})
    if not portfolio:
        raise HTTPException(status_code=400, detail="dataset_id is required for dataset-bound simulation")
    result = service.simulate(portfolio, payload.get("changes", {}), payload.get("name", "Custom scenario"))
    result["baseline_source"] = "caller_supplied_metrics"
    return result
