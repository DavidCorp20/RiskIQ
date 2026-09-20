from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.analytics.analyst_engine import AnalystEngine
from app.analytics.analyst_models import AnalystQuery, AnalystResult
from app.services.dataset_service import DatasetNotFoundError, DatasetService

router = APIRouter(prefix="/v1/analyst", tags=["analyst"])


@router.post("/query", response_model=AnalystResult)
async def analyst_query(payload: AnalystQuery) -> AnalystResult:
    """Execute a safe semantic analyst query against a resolved dataset."""
    dataset_service = DatasetService()

    try:
        dataframe = await dataset_service.get_dataset_as_dataframe(payload.dataset_id)
    except DatasetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        engine = AnalystEngine()
        return engine.execute(payload, dataframe)
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
