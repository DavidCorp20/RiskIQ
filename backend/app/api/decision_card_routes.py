from __future__ import annotations

from fastapi import APIRouter

from app.decision.decision_cards import DecisionCardService

router = APIRouter(prefix="/v1/decisions", tags=["decision-cards"])
service = DecisionCardService()


@router.post("/cards")
def build_decision_cards(payload: dict) -> dict:
    """Build UI-ready decision cards from decision recommendations."""
    recommendations = payload.get("recommendations", [])
    cards = service.build(recommendations)
    return {
        "count": len(cards),
        "cards": cards,
    }
