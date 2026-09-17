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


@router.post("/run")
def run_scenario(payload: dict) -> dict:
    """Run a sensitivity scenario from the same current point-in-time source used by Risk Analytics."""
    dataset_id = str(payload.get("dataset_id") or "").strip()
    if dataset_id:
        _require_dataset(dataset_id)
        records = persistence.portfolio_records.find({"dataset_id": dataset_id}, limit=100000)
        if not records:
            raise HTTPException(status_code=409, detail="Run the selected dataset before using the simulator")

        # Risk Analytics and the simulator must share the same canonical point-in-time
        # selection. Recomputing from portfolio_records avoids stale/incompatible
        # persisted snapshot metrics becoming a second source of truth.
        risk = risk_analytics.analyze(records)
        if not risk.get("available"):
            raise HTTPException(status_code=409, detail="No active canonical portfolio is available for stress testing")
        portfolio = {
            "balance": risk.get("exposure", 0),
            "par30": float(risk.get("par", {}).get("par30", {}).get("ratio", 0) or 0),
            "par90": float(risk.get("par", {}).get("par90", {}).get("ratio", 0) or 0),
        }
        changes = dict(payload.get("changes") or {})
        if "par_shock_points" not in changes and "shock_pct" in payload:
            changes["par_shock_points"] = payload.get("shock_pct")
        result = service.simulate(portfolio, changes, payload.get("name") or payload.get("scenario_name") or "Custom scenario")
        result["dataset_id"] = dataset_id
        result["baseline_source"] = "canonical_portfolio_risk_analytics"
        result["snapshot_date"] = risk.get("snapshot")
        return result

    # Backward-compatible low-level API for integrations that explicitly provide metrics.
    portfolio = payload.get("portfolio", {})
    if not portfolio:
        raise HTTPException(status_code=400, detail="dataset_id is required for dataset-bound simulation")
    result = service.simulate(
        portfolio,
        payload.get("changes", {}),
        payload.get("name", "Custom scenario"),
    )
    result["baseline_source"] = "caller_supplied_metrics"
    return result
