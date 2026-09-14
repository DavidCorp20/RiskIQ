from __future__ import annotations

from fastapi import APIRouter, Query

from app.analytics.analysis_catalog import catalog

router = APIRouter(prefix="/v1/analysis", tags=["analysis-catalog"])


@router.get("/catalog")
def get_analysis_catalog(fields: list[str] | None = Query(default=None)) -> dict:
    """Return the product's reusable indicators and analysis models.

    The optional fields parameter lets the frontend evaluate basic readiness
    against the canonical fields already mapped for a dataset.
    """
    return catalog(fields)
