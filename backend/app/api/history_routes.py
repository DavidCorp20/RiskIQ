from __future__ import annotations

from fastapi import APIRouter

from app.analytics.portfolio_history import PortfolioHistoryService

router = APIRouter(prefix="/v1/portfolio", tags=["portfolio-history"])
service = PortfolioHistoryService()


@router.post("/history/compare")
def compare_snapshots(payload: dict) -> dict:
    """Compare two portfolio snapshots and surface measurable deterioration/improvement."""
    return service.compare(
        current=payload.get("current", {}),
        previous=payload.get("previous", {}),
    )
