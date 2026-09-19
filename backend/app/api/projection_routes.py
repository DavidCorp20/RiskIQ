from __future__ import annotations

from fastapi import APIRouter

from app.data.portfolio_projection import PortfolioProjectionService

router = APIRouter(prefix="/v1/data", tags=["data"])
service = PortfolioProjectionService()


@router.post("/project")
def project_portfolio(rows: list[dict]) -> dict:
    """Project normalized landing rows into RiskIQ's universal portfolio model."""
    return service.project(rows)
