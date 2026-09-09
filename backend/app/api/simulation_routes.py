from __future__ import annotations

from fastapi import APIRouter

from app.simulation.scenario_simulator import ScenarioSimulator

router = APIRouter(prefix="/v1/simulator", tags=["simulator"])
service = ScenarioSimulator()


@router.post("/run")
def run_scenario(payload: dict) -> dict:
    """Run a transparent sensitivity scenario against portfolio metrics."""
    return service.simulate(
        payload.get("portfolio", {}),
        payload.get("changes", {}),
        payload.get("name", "Custom scenario"),
    )
