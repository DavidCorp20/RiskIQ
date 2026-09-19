from __future__ import annotations

from fastapi import APIRouter

from app.analytics.portfolio_intelligence import PortfolioIntelligenceService

router = APIRouter(prefix="/v1/portfolio", tags=["portfolio-intelligence"])
service = PortfolioIntelligenceService()


@router.post("/analyze")
def analyze_portfolio(rows: list[dict]) -> dict:
    """Analyze normalized loan-level rows and identify segments and deterministic risk drivers."""
    return service.analyze(rows)
