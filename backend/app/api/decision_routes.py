from __future__ import annotations

from fastapi import APIRouter

from app.decision.decision_intelligence import DecisionIntelligenceService

router = APIRouter(prefix="/v1/decisions", tags=["decision-intelligence"])
service = DecisionIntelligenceService()


@router.post("/recommend")
def recommend_decisions(payload: dict) -> dict:
    """Generate evidence-based, human-reviewable recommendations."""
    return service.build(payload.get("risk_facts", {}), payload.get("drivers", []))
