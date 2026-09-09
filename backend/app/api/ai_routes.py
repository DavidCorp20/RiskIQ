from __future__ import annotations

from fastapi import APIRouter

from app.ai.copilot import RiskCopilotService

router = APIRouter(prefix="/v1/ai", tags=["ai"])
service = RiskCopilotService()


@router.post("/copilot")
def copilot(payload: dict) -> dict:
    return service.answer(
        question=str(payload.get("question", "")),
        risk_facts=payload.get("risk_facts", {}),
        drivers=payload.get("drivers", []),
        decisions=payload.get("decisions", []),
    )
