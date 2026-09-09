from __future__ import annotations

from fastapi import APIRouter

from app.analytics.vintage_rollrate import VintageRollRateService

router = APIRouter(prefix="/v1/portfolio", tags=["vintage-roll-rate"])
service = VintageRollRateService()


@router.post("/vintage")
def analyze_vintage(rows: list[dict]) -> dict:
    """Calculate vintage cohorts and delinquency buckets without inventing historical roll rates."""
    return service.analyze(rows)
