from __future__ import annotations
import hashlib,json
from copy import deepcopy
from typing import Any
from uuid import NAMESPACE_URL,uuid5
from .models import RiskEvent,RiskEventStatus,Severity
class RiskEventEngine:
    """Maps deterministic EWS observations to stable, immutable event contracts."""
    SEVERITY_ORDER={"normal":Severity.LOW,"watch":Severity.MEDIUM,"high":Severity.HIGH,"critical":Severity.CRITICAL}
    SIGNAL_SEVERITY={"low":Severity.LOW,"medium":Severity.MEDIUM,"high":Severity.HIGH,"critical":Severity.CRITICAL}
    @staticmethod
    def _hash(value:Any)->str:
        return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    def detect(self,dataset_id:str,ews_results:list[dict[str,Any]],snapshot_id:str|None=None)->list[RiskEvent]:
        events=[]
        for result in ews_results:
            features=dict(result.get("features") or {}); signals=list(result.get("signals") or [])
            loan_id=str(result.get("loan_id") or features.get("loan_id") or "") or None
            snapshot_date=str(result.get("snapshot_date") or features.get("snapshot_date") or "") or None
            for signal in signals:
                code=str(signal.get("code") or "EWS_SIGNAL").upper(); observed=signal.get("value")
                sev=str(signal.get("severity") or result.get("band") or "low").lower()
                severity=self.SIGNAL_SEVERITY.get(sev,self.SEVERITY_ORDER.get(str(result.get("band") or "normal").lower(),Severity.LOW))
                key=f"{dataset_id}:{snapshot_id or snapshot_date or 'unknown'}:{loan_id or 'portfolio'}:{code}:{self._hash(observed)}"
                evidence=deepcopy({"ews_score":result.get("score"),"ews_band":result.get("band"),"signal":signal,"features":features,"methodology":"deterministic-observed-trajectory-v1","predictive_probability":False})
                yield_event=RiskEvent(event_id=str(uuid5(NAMESPACE_URL,key)),dataset_id=dataset_id,event_type=code,severity=severity,status=RiskEventStatus.OPEN,metric=code,observed_value=observed,threshold=self._threshold(code,observed),exposure=float(features.get("current_balance") or 0),evidence=evidence,snapshot_id=snapshot_id,snapshot_date=snapshot_date,loan_id=loan_id,event_key=key)
                events.append(yield_event)
        return events
    @staticmethod
    def _threshold(code:str,observed:Any)->Any|None:
        if code=="DPD_SEVERITY":
            try:
                value=float(observed); return 90 if value>=90 else 60 if value>=60 else 30 if value>=30 else 1
            except (TypeError,ValueError): return None
        return None
