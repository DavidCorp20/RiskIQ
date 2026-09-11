from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.schemas import DecisionRule
from app.decision.rule_repository import DecisionRuleRepository
from app.engine.decision_engine import DecisionEngine
from app.decision.rule_builder import RuleBuilder

router = APIRouter(prefix="/v1/decision-builder", tags=["decision-builder"])
service = RuleBuilder()
engine = DecisionEngine()
rules_repo = DecisionRuleRepository()


@router.get("/rules")
def list_rules(dataset_id: str | None = None, business_id: str | None = None) -> dict:
    return {"items": rules_repo.list(dataset_id=dataset_id, business_id=business_id)}


@router.post("/validate")
def validate_rule(payload: dict) -> dict:
    return service.from_visual(payload)


@router.post("/compile")
def compile_rule(payload: dict) -> dict:
    return service.compile(payload)


@router.post("/save")
def save_rule(payload: dict) -> dict:
    compiled = service.compile(payload.get("rule", payload))
    if not compiled["valid"]:
        raise HTTPException(status_code=422, detail=compiled["errors"])
    saved = rules_repo.save(compiled["compiled_rule"], payload.get("dataset_id"), payload.get("business_id"))
    return {"saved": True, "rule": saved}


@router.post("/evaluate")
def evaluate_rule(payload: dict) -> dict:
    compiled = service.compile(payload.get("rule", {}))
    if not compiled["valid"]:
        raise HTTPException(status_code=422, detail=compiled["errors"])
    rule = DecisionRule.model_validate(compiled["compiled_rule"])
    result = engine.evaluate(payload.get("facts", {}), [rule])
    return {"compiled_rule": compiled["compiled_rule"], "result": result, "execution_mode": "test_only", "customer_actions_executed": False}
