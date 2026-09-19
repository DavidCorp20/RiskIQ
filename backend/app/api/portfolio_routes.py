from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.risk_analytics_service import RiskAnalyticsDashboardService

router = APIRouter(prefix="/v1/portfolio", tags=["portfolio-dashboard"])
service = RiskAnalyticsDashboardService()


@router.get("/{dataset_id}/dashboard")
def portfolio_dashboard(
    dataset_id: str,
    segment: str | None = Query(default=None),
    cutoff_date: str | None = Query(default=None),
) -> dict:
    try:
        return service.build_portfolio_dashboard(
            dataset_id=dataset_id,
            segment=segment,
            cutoff_date=cutoff_date,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Dataset not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
