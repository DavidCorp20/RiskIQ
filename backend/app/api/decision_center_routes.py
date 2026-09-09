from __future__ import annotations

from fastapi import APIRouter

from app.decision.decision_center import DecisionCenterService

router = APIRouter(prefix="/v1/decision-center", tags=["decision-center"])
service = DecisionCenterService()


@router.post("")
def build_decision_center(payload: dict) -> dict:
    """Build the executive decision view from a pipeline response."""
    return service.build(
        pipeline=payload.get("pipeline", {}),
        history_entries=payload.get("history_entries", []),
    )
