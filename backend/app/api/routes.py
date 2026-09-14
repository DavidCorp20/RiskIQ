from fastapi import APIRouter, Query

from app.analytics.analysis_catalog import catalog
from app.api.schemas import DecisionRequest, DecisionResponse
from app.engine.decision_engine import DecisionEngine

router = APIRouter()
engine = DecisionEngine()


@router.get("/v1/status", tags=["system"])
def status() -> dict[str, str]:
    return {"status": "ready", "engine": "decision-engine"}


@router.get("/v1/analysis/catalog", tags=["analysis"])
def analysis_catalog(fields: list[str] | None = Query(default=None)) -> dict:
    """Expose the reusable indicator/model catalog for the MVP workspace."""
    return catalog(fields)


@router.post("/v1/decisions/evaluate", response_model=DecisionResponse, tags=["decisions"])
def evaluate_decision(request: DecisionRequest) -> DecisionResponse:
    result = engine.evaluate(request.facts, request.rules)
    return DecisionResponse(**result)
