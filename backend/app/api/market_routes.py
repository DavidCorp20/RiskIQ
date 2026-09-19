from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.market.correlation import RiskMarketCorrelationEngine
from app.market.models import StatisticalEvidence
from app.market.service import MarketContextService

router = APIRouter(prefix="/v1/market", tags=["market-intelligence"])
market_context_service = MarketContextService()
correlation_engine = RiskMarketCorrelationEngine()


@router.get("/context")
async def market_context() -> dict[str, Any]:
    """Return the normalized external context contract used by analytical Copilot."""
    return await market_context_service.get_context()


@router.post("/correlations")
def classify_correlation(payload: dict[str, Any]) -> dict[str, Any]:
    statistical = payload.get("statistical_evidence")
    evidence = StatisticalEvidence.model_validate(statistical) if isinstance(statistical, dict) else None
    finding = correlation_engine.classify(
        portfolio_observation=payload.get("portfolio_observation") or {},
        market_observation=payload.get("market_observation"),
        statistical_evidence=evidence,
        causal_evidence=payload.get("causal_evidence"),
    )
    return finding.model_dump(mode="json")
