from __future__ import annotations

from fastapi import APIRouter

from app.analytics.learning_loop import DecisionLearningService

router = APIRouter(prefix="/v1/learning", tags=["learning"])
service = DecisionLearningService()


@router.post("/summary")
def learning_summary(payload: dict) -> dict:
    """Summarize observed outcomes of historical decisions."""
    return service.summarize(payload.get("entries", []))
