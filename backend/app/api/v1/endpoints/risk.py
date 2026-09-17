from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.analytics.risk_analytics import (
    RiskAnalyticsIntegrityError,
    RiskAnalyticsService,
)
from app.repositories.risk_repository import RiskAnalysisRepository
from app.schemas.risk import RiskAnalyticsRequest, RiskAnalyticsResponse

router = APIRouter(prefix="/v1/risk", tags=["risk-analytics"])
service = RiskAnalyticsService()


@router.post(
    "/analytics",
    response_model=RiskAnalyticsResponse,
    status_code=status.HTTP_200_OK,
)
def analyze_risk(
    request: RiskAnalyticsRequest,
    persist: bool = Query(False, description="Persist the successful analysis in MongoDB."),
) -> RiskAnalyticsResponse:
    """Run deterministic analytics and optionally persist the canonical result.

    Persistence is deliberately downstream of the deterministic calculation. A
    MongoDB failure never invalidates a successful risk calculation.
    """
    rows = [
        row.model_dump() if hasattr(row, "model_dump") else row
        for row in request.rows
    ]

    try:
        result = service.analyze(rows)
    except RiskAnalyticsIntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "risk_integrity_error",
                "message": str(exc),
                "dataset_id": request.dataset_id,
            },
        ) from exc

    response_metadata: dict[str, object] = {
        "persistence": {
            "requested": persist,
            "persisted": False,
        }
    }
    result_id: str | None = None

    if persist:
        try:
            repository = RiskAnalysisRepository()
            result_id = repository.save_analysis(
                dataset_id=request.dataset_id or "adhoc",
                payload=result,
            )
            response_metadata["persistence"] = {
                "requested": True,
                "persisted": True,
            }
        except Exception as exc:
            response_metadata["persistence"] = {
                "requested": True,
                "persisted": False,
                "warning": "Risk analysis calculated successfully, but persistence failed.",
                "error_type": type(exc).__name__,
            }

    return RiskAnalyticsResponse(
        **result,
        result_id=result_id,
        metadata=response_metadata,
    )
