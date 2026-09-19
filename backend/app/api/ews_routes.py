from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.analytics.ews_engine import EWSEngine
from app.data.persistence import PortfolioPersistenceService

router = APIRouter(prefix="/v1/ews", tags=["early-warning"])
engine = EWSEngine()
persistence = PortfolioPersistenceService()


@router.post("/calculate")
def calculate_ews(payload: dict) -> dict:
    """Calculate deterministic Early Warning scores from historical observations."""
    rows = payload.get("rows") or []
    dataset_id = payload.get("dataset_id")
    if not rows and dataset_id:
        rows = persistence.portfolio_records.find(
            {"dataset_id": dataset_id},
            limit=100000,
        )
    if not isinstance(rows, list) or not rows:
        raise HTTPException(
            status_code=422,
            detail="rows or dataset_id with historical portfolio observations is required",
        )

    try:
        results = engine.calculate(rows)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "status": "calculated",
        "dataset_id": dataset_id,
        "methodology": "deterministic-observed-trajectory-v1",
        "predictive_probability": False,
        "count": len(results),
        "results": results,
    }
