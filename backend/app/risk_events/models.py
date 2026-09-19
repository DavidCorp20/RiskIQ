from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class Severity(str, Enum):
    LOW="LOW"; MEDIUM="MEDIUM"; HIGH="HIGH"; CRITICAL="CRITICAL"
class RiskEventStatus(str, Enum):
    OPEN="OPEN"; ACKNOWLEDGED="ACKNOWLEDGED"; ACTION_REQUIRED="ACTION_REQUIRED"; RESOLVED="RESOLVED"; DISMISSED="DISMISSED"
class ActionType(str, Enum):
    REVIEW="REVIEW"; COLLECTIONS="COLLECTIONS"; POLICY_REVIEW="POLICY_REVIEW"; ESCALATION="ESCALATION"; COMPLIANCE="COMPLIANCE"
class ActionStatus(str, Enum):
    PENDING="PENDING"; IN_PROGRESS="IN_PROGRESS"; COMPLETED="COMPLETED"; CANCELLED="CANCELLED"

class RiskEvent(BaseModel):
    model_config=ConfigDict(frozen=True, extra="forbid")
    event_id:str; dataset_id:str; event_type:str; severity:Severity; status:RiskEventStatus=RiskEventStatus.OPEN
    metric:str; observed_value:Any; threshold:Any|None=None; exposure:float=0.0; evidence:dict[str,Any]=Field(default_factory=dict)
    snapshot_id:str|None=None; snapshot_date:str|None=None; loan_id:str|None=None; event_key:str
    created_at:datetime=Field(default_factory=lambda:datetime.now(timezone.utc)); updated_at:datetime=Field(default_factory=lambda:datetime.now(timezone.utc))

class RiskAction(BaseModel):
    model_config=ConfigDict(frozen=True, extra="forbid")
    action_id:str; event_id:str; action_type:ActionType; priority:int=Field(ge=1,le=4); status:ActionStatus=ActionStatus.PENDING
    owner:str; rationale:str; evidence:dict[str,Any]=Field(default_factory=dict); due_at:datetime|None=None
    external_ticket_id:str|None=None; created_at:datetime=Field(default_factory=lambda:datetime.now(timezone.utc)); updated_at:datetime=Field(default_factory=lambda:datetime.now(timezone.utc))
