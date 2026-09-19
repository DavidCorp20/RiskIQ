from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _clamp(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return max(0.0, min(1.0, number))


class PortfolioKPI(BaseModel):
    model_config = ConfigDict(extra="forbid")
    formatted: str
    subtext: str | None = None


class RatingDistributionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rating: str
    exposure: float


class HeatmapItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    row: str
    column: str
    label: str
    formatted_exposure: str
    formatted_risk: str
    risk_intensity: float = Field(ge=0.0, le=1.0)

    @field_validator("risk_intensity", mode="before")
    @classmethod
    def clamp_intensity(cls, value: Any) -> float:
        return _clamp(value)


class VintageItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vintage: str
    formatted_value: str
    formatted_exposure: str
    risk_intensity: float = Field(ge=0.0, le=1.0)

    @field_validator("risk_intensity", mode="before")
    @classmethod
    def clamp_intensity(cls, value: Any) -> float:
        return _clamp(value)


class RiskDriverItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    description: str
    value: str


class PortfolioFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    segments: list[str] = Field(default_factory=list)
    cutoff_dates: list[str] = Field(default_factory=list)


class PortfolioDashboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str = "portfolio-dashboard-v1"
    dataset_id: str
    snapshot_date: str | None = None
    kpis: dict[str, PortfolioKPI]
    rating_distribution: list[RatingDistributionItem]
    heatmap: list[HeatmapItem]
    vintage: list[VintageItem]
    risk_drivers: list[RiskDriverItem]
    filters: PortfolioFilters

    # Compatibility contract consumed by the current React dashboard.
    structure: dict[str, Any] = Field(default_factory=dict)
    concentration: dict[str, Any] = Field(default_factory=dict)
    vintage_view: dict[str, Any] = Field(default_factory=dict)

    @field_validator("kpis")
    @classmethod
    def validate_kpis(cls, value: dict[str, PortfolioKPI]) -> dict[str, PortfolioKPI]:
        required = {"exposure", "active_loans", "par30", "par60", "par90", "npl"}
        missing = required - set(value)
        if missing:
            raise ValueError(f"Missing KPI keys: {sorted(missing)}")
        return value
