from __future__ import annotations

from fastapi import APIRouter

from app.decision.rule_builder import RuleBuilder

router = APIRouter(prefix="/v1/decision-builder", tags=["decision-builder"])
service = RuleBuilder()


@router.post("/validate")
def validate_rule(payload: dict) -> dict:
    return service.from_visual(payload)
