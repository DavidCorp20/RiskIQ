from typing import Any

from pydantic import BaseModel, Field


class RuleCondition(BaseModel):
    field: str
    operator: str
    value: Any


class RuleAction(BaseModel):
    type: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class DecisionRule(BaseModel):
    id: str
    name: str
    conditions: list[RuleCondition] = Field(default_factory=list)
    actions: list[RuleAction] = Field(default_factory=list)
    mode: str = "suggested"
    enabled: bool = True


class DecisionRequest(BaseModel):
    facts: dict[str, Any]
    rules: list[DecisionRule] = Field(default_factory=list)


class DecisionResponse(BaseModel):
    triggered_rules: list[str]
    actions: list[dict[str, Any]]
    evaluation_trace: list[dict[str, Any]]
