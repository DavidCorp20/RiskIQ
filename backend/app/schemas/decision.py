from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


RuleSeverity = Literal["INFO", "WARNING", "CRITICAL"]
DecisionStatus = Literal["APPROVED", "FLAGGED", "ACTION_REQUIRED"]


class PolicyRuleResult(BaseModel):
    """Auditable result for one deterministic credit policy rule."""

    rule_id: str
    name: str
    severity: RuleSeverity
    triggered: bool
    metric_value: float | str | None = None
    message: str


class DecisionAssessmentResponse(BaseModel):
    """Deterministic policy assessment over one canonical risk analysis."""

    dataset_id: str
    result_id: str | None = None
    overall_status: DecisionStatus
    triggered_rules: list[PolicyRuleResult] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    evaluated_at: str


class DecisionEvaluationRequest(BaseModel):
    """Input for evaluating a persisted analysis or a direct analytics payload."""

    result_id: str | None = None
    dataset_id: str | None = None
    payload: dict | None = None
