from __future__ import annotations

from fastapi import APIRouter

from app.analytics.diagnosis import DiagnosisService

router = APIRouter(prefix="/v1/diagnosis", tags=["diagnosis"])
service = DiagnosisService()


@router.post("/build")
def build_diagnosis(payload: dict) -> dict:
    """Create an evidence-backed diagnosis from deterministic analytics."""
    return service.build(
        payload.get("analysis") or {},
        data_quality=payload.get("data_quality"),
        readiness=payload.get("readiness"),
    )
