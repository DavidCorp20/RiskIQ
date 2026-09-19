from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ActionLevel = Literal["low", "medium", "high"]
RecommendationStatus = Literal[
    "proposed", "pending_approval", "approved", "rejected",
    "executed", "cancelled", "expired",
]
RecommendationAction = Literal["review", "limit_reduction", "preventive_block"]


class DecisionRecommendationModel(BaseModel):
    recommendation_id: str
    dataset_id: str
    loan_id: str | None = None
    action: RecommendationAction
    action_level: ActionLevel
    status: RecommendationStatus
    requires_human_approval: bool
    policy_id: str
    policy_version: int = Field(ge=1)
    trigger_codes: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    evidence_hash: str
    rationale: str
    source: str = "deterministic_ews"
    created_at: str
    expires_at: str | None = None
    customer_action_executed: bool = False


class DecisionLedgerEntryModel(BaseModel):
    ledger_id: str
    recommendation_id: str
    dataset_id: str
    event: str
    actor: str
    state: str
    evidence_snapshot: dict[str, Any]
    evidence_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    immutable: Literal[True] = True


class DecisionRecommendRequest(BaseModel):
    dataset_id: str
    rows: list[dict[str, Any]] = Field(default_factory=list)
    high_score: float = 50.0
    policy_id: str = "ews-action-policy"
    policy_version: int = Field(default=1, ge=1)
