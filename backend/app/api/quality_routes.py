from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.data.canonical import registry
from app.data.discovery import DataDiscoveryService
from app.data.normalizer import DataNormalizer
from app.data.quality import DataQualityService

router = APIRouter(prefix="/v1/data-quality", tags=["data-quality"])
quality_service = DataQualityService()
discovery_service = DataDiscoveryService()
normalizer = DataNormalizer()


class QualityAssessRequest(BaseModel):
    rows: list[dict]
    mappings: list[dict] = []


class MappingReadinessRequest(BaseModel):
    mappings: list[dict]


@router.get("/schema")
def canonical_schema() -> dict:
    return registry()


@router.post("/discover")
def discover_data(rows: list[dict]) -> dict:
    return discovery_service.discover(rows)


@router.post("/assess")
def assess_quality(payload: QualityAssessRequest) -> dict:
    return quality_service.assess(payload.rows, mappings=payload.mappings)


@router.post("/readiness")
def normalization_readiness(payload: MappingReadinessRequest) -> dict:
    from app.data.normalizer import FieldMapping
    parsed = [FieldMapping(**item) for item in payload.mappings]
    return normalizer.mapping_summary(parsed)
