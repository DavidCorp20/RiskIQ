from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.analytics.ews_engine import EWSEngine
from app.analytics.portfolio_ews import PortfolioEWSService
from app.data.persistence import PortfolioPersistenceService

router = APIRouter(prefix="/v1/ews", tags=["early-warning"])
engine = EWSEngine()
portfolio_service = PortfolioEWSService(engine)
persistence = PortfolioPersistenceService()


def _rows(payload: dict) -> tuple[list[dict], str | None]:
    rows = payload.get("rows") or []
    dataset_id = payload.get("dataset_id")
    if not rows and dataset_id:
        rows = persistence.portfolio_records.find({"dataset_id": dataset_id}, limit=100000)
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=422, detail="rows or dataset_id with historical portfolio observations is required")
    return rows, dataset_id


@router.post("/calculate")
def calculate_ews(payload: dict) -> dict:
    rows, dataset_id = _rows(payload)
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


@router.post("/portfolio-summary")
def portfolio_ews_summary(payload: dict) -> dict:
    rows, dataset_id = _rows(payload)
    try:
        summary = portfolio_service.summarize(
            rows,
            high_score=float(payload.get("high_score", 50.0)),
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "status": "calculated",
        "dataset_id": dataset_id,
        **summary,
    }
