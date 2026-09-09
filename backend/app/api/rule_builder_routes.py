from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.engine.decision_engine import DecisionEngine
from app.decision.rule_builder import RuleBuilder

router = APIRouter(prefix="/v1/decision-builder", tags=["decision-builder"])
service = RuleBuilder()
engine = DecisionEngine()


@router.post("/validate")
def validate_rule(payload: dict) -> dict:
    return service.from_visual(payload)


@router.post("/compile")
def compile_rule(payload: dict) -> dict:
    """Compile a visual rule into the declarative Decision Engine contract."""
    return service.compile(payload)


@router.post("/evaluate")
def evaluate_rule(payload: dict) -> dict:
    """Compile a visual rule and test it against supplied facts."""
    compiled = service.compile(payload.get("rule", {}))
    if not compiled["valid"]:
        raise HTTPException(status_code=422, detail=compiled["errors"])
    result = engine.evaluate(payload.get("facts", {}), [compiled["compiled_rule"]])
    return {
        "compiled_rule": compiled["compiled_rule"],
        "result": result,
        "execution_mode": "test_only",
        "customer_actions_executed": False,
    }
