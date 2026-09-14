from __future__ import annotations

from fastapi import APIRouter

from app.data.canonical import registry
from app.data.discovery import DataDiscoveryService
from app.data.normalizer import DataNormalizer
from app.data.quality import DataQualityService

router = APIRouter(prefix="/v1/data-quality", tags=["data-quality"])
quality_service = DataQualityService()
discovery_service = DataDiscoveryService()
normalizer = DataNormalizer()


@router.get("/schema")
def canonical_schema() -> dict:
    """Return the universal financial vocabulary used by RiskIQ analytics."""
    return registry()


@router.post("/discover")
def discover_data(rows: list[dict]) -> dict:
    """Profile source columns and propose canonical mappings."""
    return discovery_service.discover(rows)


@router.post("/assess")
def assess_quality(rows: list[dict], mappings: list[dict] | None = None) -> dict:
    """Assess data quality and expose row/column errors plus analysis impact."""
    return quality_service.assess(rows, mappings=mappings)


@router.post("/readiness")
def normalization_readiness(mappings: list[dict]) -> dict:
    """Check whether mappings cover the minimum canonical model."""
    from app.data.normalizer import FieldMapping

    parsed = [FieldMapping(**item) for item in mappings]
    return normalizer.mapping_summary(parsed)
