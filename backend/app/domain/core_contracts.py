from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4
from pydantic import BaseModel, Field

def utc_now() -> datetime: return datetime.now(timezone.utc)
class PortfolioObservationContract(BaseModel):
    loan_id: str
    customer_id: str | None = None
    snapshot_date: str | None = None
    dpd: float = 0
    outstanding_principal: float = 0
    product_id: str | None = None
    segment: str | None = None
    origination_date: str | None = None
    due_date: str | None = None
    status: str | None = None
    model_config = {"extra": "allow"}
class RiskMetricContract(BaseModel):
    name: str; value: float | int | str | None; unit: str; as_of: str | None = None; methodology: str; source: Literal["deterministic"] = "deterministic"
class RiskFactContract(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    code: str; value: Any; evidence: dict[str, Any] = Field(default_factory=dict); source: Literal["deterministic"] = "deterministic"
class DecisionContract(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    status: Literal["not_triggered","proposed","executed"]
    decision: str | None = None; triggered_rules: list[str] = Field(default_factory=list); reason_codes: list[str] = Field(default_factory=list); actions: list[dict[str, Any]] = Field(default_factory=list); evaluation_trace: list[dict[str, Any]] = Field(default_factory=list)
class AuditEventContract(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str; occurred_at: datetime = Field(default_factory=utc_now); actor: str = "system"; dataset_id: str | None = None; snapshot_id: str | None = None; decision_id: str | None = None; evidence: dict[str, Any] = Field(default_factory=dict)
class RiskRunContract(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    contract_version: str = "risk-core-v1"; dataset_id: str | None = None; snapshot_id: str | None = None; observations: int; exposure: float; metrics: list[RiskMetricContract] = Field(default_factory=list); facts: list[RiskFactContract] = Field(default_factory=list); decision: DecisionContract | None = None; audit: AuditEventContract; methodology: dict[str, Any] = Field(default_factory=dict)
