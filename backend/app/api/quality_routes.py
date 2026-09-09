from __future__ import annotations

from fastapi import APIRouter

from app.data.quality import DataQualityService

router = APIRouter(prefix="/v1/data-quality", tags=["data-quality"])
service = DataQualityService()


@router.post("/assess")
def assess_quality(rows: list[dict]) -> dict:
    """Return deterministic quality score and blocking issues for normalized rows."""
    return service.assess(rows)
