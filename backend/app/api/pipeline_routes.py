from __future__ import annotations

from fastapi import APIRouter

from app.decision.decision_pipeline import DecisionPipelineService

router = APIRouter(prefix="/v1/decisions", tags=["decision-pipeline"])
service = DecisionPipelineService()


@router.post("/pipeline")
def run_decision_pipeline(payload: dict) -> dict:
    """Run analytics, custom rules, recommendations and decision cards together."""
    return service.build(
        current=payload.get("current", {}),
        previous=payload.get("previous", {}),
        current_analysis=payload.get("current_analysis"),
        custom_rules=payload.get("custom_rules", []),
    )
