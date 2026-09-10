from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.data.persistence import PortfolioPersistenceService
from app.simulation.scenario_simulator import ScenarioSimulator

router = APIRouter(prefix="/v1/simulator", tags=["simulator"])
service = ScenarioSimulator()
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
    """Run a transparent sensitivity scenario against a persisted dataset snapshot."""
    dataset_id = str(payload.get("dataset_id") or "").strip()
    if dataset_id:
        _require_dataset(dataset_id)
        snapshot = _latest_snapshot(dataset_id)
        portfolio = {
            "balance": snapshot.get("outstanding_balance", 0),
            "par30": snapshot.get("par30", 0),
            "par90": snapshot.get("par90", 0),
        }
        result = service.simulate(
            portfolio,
            payload.get("changes", {}),
            payload.get("name", "Custom scenario"),
        )
        result["dataset_id"] = dataset_id
        result["baseline_source"] = "persisted_snapshot"
        result["snapshot_date"] = snapshot.get("snapshot_date")
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
