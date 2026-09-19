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




class TimeSeriesPoint(BaseModel):
    date: date
    value: float


class HistoricalSeries(BaseModel):
    name: str
    source: str
    frequency: str = "monthly"
    unit: str | None = None
    points: list[TimeSeriesPoint] = Field(default_factory=list)


class PortfolioTimeSeriesPoint(TimeSeriesPoint):
    metric: str


class PortfolioTimeSeriesRequest(BaseModel):
    portfolio_series: list[HistoricalSeries]
    market_series: list[HistoricalSeries]
    frequency: str = "monthly"
    tolerance_days: int = Field(default=3, ge=0, le=31)
    exclude_weekends: bool = True
    prefer_previous: bool = True
    portfolio_transformation: str = "level"
    market_transformation: str = "level"
    methods: list[str] = Field(default_factory=lambda: ["pearson", "spearman"])
    min_sample_size: int = Field(default=12, ge=12)
    alpha: float = Field(default=0.05, gt=0, lt=1)
\n\nclass StatisticalEvidence(BaseModel):
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
