from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EvidenceClassification(str, Enum):
    OBSERVED = "OBSERVED"
    CORRELATED = "CORRELATED"
    POSSIBLE_EXPLANATION = "POSSIBLE EXPLANATION"
    CAUSALITY_CONFIRMED = "CAUSALITY CONFIRMED"


class MarketIndicator(BaseModel):
    symbol: str
    value: float
    previous_value: float | None = None
    change_pct: float | None = None
    unit: str | None = None
    observed_at: str | None = None
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MacroEvent(BaseModel):
    event_id: str
    name: str
    category: str
    country: str | None = None
    event_date: date | None = None
    impact: str | None = None
    description: str | None = None
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketContext(BaseModel):
    as_of: str
    market_indicators: dict[str, MarketIndicator] = Field(default_factory=dict)
    macro_events: list[MacroEvent] = Field(default_factory=list)
    status: str = "unavailable"
    errors: list[str] = Field(default_factory=list)
    source: str = "RiskIQ Market Intelligence Layer"
    cache: str = "miss"
    ttl_seconds: int = 60


class StatisticalEvidence(BaseModel):
    metric: str
    market_indicator: str
    coefficient: float | None = None
    p_value: float | None = None
    sample_size: int | None = None
    method: str | None = None
    validated: bool = False
    validation_notes: str | None = None


class CorrelationFinding(BaseModel):
    classification: EvidenceClassification
    statement: str
    portfolio_metric: str | None = None
    market_indicator: str | None = None
    statistical_evidence: StatisticalEvidence | None = None
    causal_evidence: dict[str, Any] | None = None
