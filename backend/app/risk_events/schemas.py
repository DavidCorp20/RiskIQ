from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field
from .models import ActionStatus, RiskEventStatus
class RiskEventDetectionRequest(BaseModel):
    dataset_id:str; ews_results:list[dict[str,Any]]=Field(default_factory=list); snapshot_id:str|None=None; auto_orchestrate:bool=True
class RiskEventStatusUpdate(BaseModel): status:RiskEventStatus
class RiskActionStatusUpdate(BaseModel): status:ActionStatus
