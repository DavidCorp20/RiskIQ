from __future__ import annotations
from pydantic import BaseModel, Field

class PDRating(BaseModel):
    entity_id: str
    horizon_periods: int = Field(ge=1)
    pd: float = Field(ge=0, le=1)
    method: str
    evidence_count: int = Field(ge=0)

class TransitionMatrix(BaseModel):
    states: list[str]
    probabilities: dict[str, dict[str, float]]
    counts: dict[str, dict[str, int]]
    sample_size: int = Field(ge=0)
    methodology: str

class SurvivalPoint(BaseModel):
    period: int = Field(ge=0)
    at_risk: int = Field(ge=0)
    events: int = Field(ge=0)
    survival: float = Field(ge=0, le=1)

class SurvivalCurve(BaseModel):
    points: list[SurvivalPoint]
    methodology: str
    sample_size: int = Field(ge=0)

class FeatureImportance(BaseModel):
    feature: str
    metric: str
    value: float
    direction: str
    sample_size: int
