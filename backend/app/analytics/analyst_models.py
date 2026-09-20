from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

FilterOperator = Literal["eq","neq","gt","gte","lt","lte","in","not_in","contains"]

class AnalystDimension(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    field: str = Field(min_length=1, max_length=128)
    label: str | None = Field(default=None, max_length=160)
    @field_validator("field")
    @classmethod
    def valid_field(cls, v: str) -> str:
        if v.startswith("_") or "." in v: raise ValueError("dimension field must be a simple column name")
        return v

class AnalystMeasure(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=64)
    field: str | None = Field(default=None, max_length=128)
    label: str | None = Field(default=None, max_length=160)

class AnalystFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str = Field(min_length=1, max_length=128)
    operator: FilterOperator
    value: Any
    @field_validator("field")
    @classmethod
    def valid_field(cls, v: str) -> str:
        if v.startswith("_") or "." in v: raise ValueError("filter field must be a simple column name")
        return v

class AnalystBucketRange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min: float
    max: float | None = None
    label: str = Field(min_length=1, max_length=80)
    @field_validator("max")
    @classmethod
    def valid_bounds(cls, v: float | None, info) -> float | None:
        lo = info.data.get("min")
        if v is not None and lo is not None and v <= lo: raise ValueError("bucket max must be greater than min")
        return v

class AnalystBucket(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    field: str = Field(min_length=1, max_length=128)
    type: Literal["range"] = "range"
    ranges: list[AnalystBucketRange] = Field(min_length=1, max_length=100)
    output_field: str | None = Field(default=None, max_length=128)

class AnalystQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_id: str = Field(min_length=1, max_length=128)
    dimensions: list[AnalystDimension] = Field(default_factory=list, max_length=8)
    measures: list[AnalystMeasure] = Field(min_length=1, max_length=16)
    filters: list[AnalystFilter] = Field(default_factory=list, max_length=32)
    bucket: AnalystBucket | None = None
    @field_validator("measures")
    @classmethod
    def unique_measures(cls, v):
        names=[m.name for m in v]
        if len(names)!=len(set(names)): raise ValueError("measure names must be unique")
        return v
    @field_validator("dimensions")
    @classmethod
    def unique_dimensions(cls, v):
        fields=[d.field for d in v]
        if len(fields)!=len(set(fields)): raise ValueError("dimension fields must be unique")
        return v

class AnalystResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_id: str
    dimensions: list[str]
    measures: list[str]
    rows: list[dict[str, Any]]
    row_count: int = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
