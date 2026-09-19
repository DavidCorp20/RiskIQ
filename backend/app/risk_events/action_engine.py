from __future__ import annotations
from datetime import datetime,timedelta,timezone
from uuid import NAMESPACE_URL,uuid5
from .models import ActionStatus,ActionType,RiskAction,RiskEvent,Severity
class ActionEngine:
    """Deterministic event-to-action policy; no AI participates in routing."""
    def create_action(self,event:RiskEvent)->RiskAction:
        action_type,priority,owner,rationale,days=self._policy(event)
        return RiskAction(action_id=str(uuid5(NAMESPACE_URL,f"{event.event_id}:{action_type.value}")),event_id=event.event_id,action_type=action_type,priority=priority,status=ActionStatus.PENDING,owner=owner,rationale=rationale,evidence=dict(event.evidence),due_at=datetime.now(timezone.utc)+timedelta(days=days))
    @staticmethod
    def _policy(event:RiskEvent):
        if event.event_type in {"DPD_SEVERITY","DPD_DETERIORATION","BUCKET_MIGRATION"}:
            if event.severity==Severity.CRITICAL:return ActionType.ESCALATION,1,"risk_committee","Critical deterioration requires immediate risk escalation.",1
            if event.severity==Severity.HIGH:return ActionType.COLLECTIONS,1,"collections","Observed delinquency deterioration requires collections review.",2
            return ActionType.REVIEW,2,"risk_analyst","Observed delinquency signal requires analyst review.",5
        if event.event_type=="PD_DETERIORATION":return ActionType.POLICY_REVIEW,2,"credit_risk","Observed PD deterioration requires underwriting/policy review.",5
        if event.event_type=="EXPOSURE_MATERIAL":return ActionType.REVIEW,3,"risk_analyst","Material exposure amplifies operational priority.",7
        return ActionType.REVIEW,3,"risk_analyst","Risk event requires deterministic analyst review.",7
