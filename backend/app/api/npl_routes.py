from __future__ import annotations

from fastapi import APIRouter

from app.analytics.npl import NPLAnalyticsService

router = APIRouter(prefix="/v1/risk", tags=["risk"])
service = NPLAnalyticsService()


@router.post("/npl")
def npl(rows: list[dict]) -> dict:
    return service.analyze(rows)
