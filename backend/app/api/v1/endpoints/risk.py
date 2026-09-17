from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.analytics.risk_analytics import (
    RiskAnalyticsIntegrityError,
    RiskAnalyticsService,
)
from app.schemas.risk import RiskAnalyticsRequest, RiskAnalyticsResponse

router = APIRouter(prefix="/v1/risk", tags=["risk-analytics"])
service = RiskAnalyticsService()


@router.post(
    "/analytics",
    response_model=RiskAnalyticsResponse,
    status_code=status.HTTP_200_OK,
)
def analyze_risk(request: RiskAnalyticsRequest) -> RiskAnalyticsResponse:
    """Run deterministic portfolio risk analytics for the supplied observations."""
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

    return RiskAnalyticsResponse(**result)
