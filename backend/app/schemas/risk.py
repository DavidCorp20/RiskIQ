from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LoanRowSchema(BaseModel):
    """Canonical transport representation of one credit observation."""

    model_config = ConfigDict(extra="allow")

    loan_id: str
    outstanding_principal: float
    dpd: float = 0
    segment: str | None = None
    origination_date: str | None = None
    snapshot_date: str | None = None
    product_id: str | None = None


class RiskAnalyticsRequest(BaseModel):
    """Input contract for deterministic portfolio risk analytics."""

    rows: list[LoanRowSchema | dict[str, Any]] = Field(min_length=1)
    dataset_id: str | None = None


class RiskAnalyticsResponse(BaseModel):
    """Canonical output contract returned by the risk analytics engine."""

    available: bool
    loan_count: int
    exposure: float
    par: dict[str, Any]
    dpd_buckets: dict[str, Any]
    integrity: dict[str, Any]
    concentration: dict[str, Any]
    vintage: list[dict[str, Any]]
    drivers: list[dict[str, Any]]
    migration: dict[str, Any]
    deterioration_drivers: list[dict[str, Any]]
    methodology: dict[str, Any]
    snapshot: str
    result_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
