from copy import deepcopy
from app.risk_events.action_engine import ActionEngine
from app.risk_events.event_engine import RiskEventEngine
from app.risk_events.models import ActionType,RiskEventStatus

def _ews():
    return [{"loan_id":"L-1","snapshot_date":"2026-09-19","score":82.0,"band":"critical","signals":[{"code":"DPD_SEVERITY","severity":"critical","value":95,"points":25}],"features":{"loan_id":"L-1","snapshot_date":"2026-09-19","current_balance":12000,"current_dpd":95}}]

def test_event_detection_is_deterministic():
    a=RiskEventEngine().detect("ds-1",_ews(),"snap-1")[0];b=RiskEventEngine().detect("ds-1",_ews(),"snap-1")[0];assert a.event_id==b.event_id and a.event_key==b.event_key

def test_event_evidence_cannot_be_reassigned():
    event=RiskEventEngine().detect("ds-1",_ews(),"snap-1")[0];original=deepcopy(event.evidence)
    try:event.evidence={}
    except Exception:pass
    else:assert False,"RiskEvent evidence assignment was mutable"
    assert event.evidence==original

def test_action_engine_is_deterministic():
    event=RiskEventEngine().detect("ds-1",_ews(),"snap-1")[0];action=ActionEngine().create_action(event);assert action.action_type==ActionType.ESCALATION and action.priority==1 and action.event_id==event.event_id

def test_lifecycle_status_contract():
    assert RiskEventEngine().detect("ds-1",_ews(),"snap-1")[0].status==RiskEventStatus.OPEN
