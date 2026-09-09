from fastapi import APIRouter

from app.api.schemas import DecisionRequest, DecisionResponse
from app.engine.decision_engine import DecisionEngine

router = APIRouter()
engine = DecisionEngine()


@router.get("/v1/status", tags=["system"])
def status() -> dict[str, str]:
    return {"status": "ready", "engine": "decision-engine"}


@router.post("/v1/decisions/evaluate", response_model=DecisionResponse, tags=["decisions"])
def evaluate_decision(request: DecisionRequest) -> DecisionResponse:
    result = engine.evaluate(request.facts, request.rules)
    return DecisionResponse(**result)
