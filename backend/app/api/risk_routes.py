from __future__ import annotations

from fastapi import APIRouter

from app.analytics.risk_facts import RiskFactsService

router = APIRouter(prefix="/v1/risk", tags=["risk"])
service = RiskFactsService()


@router.post("/facts")
def build_risk_facts(metrics: dict) -> dict:
    """Transform deterministic portfolio metrics into explainable risk facts and alerts."""
    return service.build(metrics)
