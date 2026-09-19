from __future__ import annotations
from fastapi import APIRouter,BackgroundTasks,HTTPException
from app.risk_events.action_engine import ActionEngine
from app.risk_events.event_engine import RiskEventEngine
from app.risk_events.models import ActionStatus,RiskEventStatus
from app.risk_events.repository import RiskActionRepository,RiskEventRepository
from app.risk_events.schemas import RiskActionStatusUpdate,RiskEventDetectionRequest,RiskEventStatusUpdate
from app.risk_events.adapters.factory import ActionAdapterFactory
from app.risk_events.lifecycle import LifecycleStatus,RiskEventLifecycle,transition,apply_recurrence,sla_deadline
from app.data.mongo import MongoRepository

router=APIRouter(prefix="/v1/risk-events",tags=["risk-events"])
event_engine=RiskEventEngine(); action_engine=ActionEngine(); events=RiskEventRepository(); actions=RiskActionRepository(); lifecycle_store=MongoRepository("risk_event_lifecycle")

@router.post("/detect")
async def detect(request:RiskEventDetectionRequest,background_tasks:BackgroundTasks):
    event_rows=[]; action_rows=[]
    for event in event_engine.detect(request.dataset_id,request.ews_results,request.snapshot_id):
        row=events.create_if_absent(event); event_rows.append(row)
        if request.auto_orchestrate:
            action=actions.create_if_absent(action_engine.create_action(event)); action_rows.append(action)
            adapter=ActionAdapterFactory.create()
            background_tasks.add_task(adapter.dispatch, action, row)
    return {"count":len(event_rows),"events":event_rows,"actions":action_rows,"idempotent":True,"action_adapter":ActionAdapterFactory.configured()}

@router.get("/actions/list")
def list_actions(event_id:str|None=None,status:ActionStatus|None=None,limit:int=500):
    rows=actions.list(event_id=event_id,status=status.value if status else None,limit=limit); return {"count":len(rows),"actions":rows}

@router.get("/actions/{action_id}")
def get_action(action_id:str):
    row=actions.get(action_id)
    if not row: raise HTTPException(status_code=404,detail="Risk action not found")
    return {"action":row}

@router.patch("/actions/{action_id}/status")
def update_action_status(action_id:str,request:RiskActionStatusUpdate):
    try:return {"action":actions.update_status(action_id,request.status)}
    except KeyError as exc:raise HTTPException(status_code=404,detail="Risk action not found") from exc

@router.get("")
def list_events(dataset_id:str|None=None,status:RiskEventStatus|None=None,limit:int=500):
    rows=events.list(dataset_id=dataset_id,status=status.value if status else None,limit=limit); return {"count":len(rows),"events":rows}

@router.get("/{event_id}")
def get_event(event_id:str):
    row=events.get(event_id)
    if not row: raise HTTPException(status_code=404,detail="Risk event not found")
    return {"event":row,"actions":actions.list(event_id=event_id)}

@router.patch("/{event_id}/status")
def update_event_status(event_id:str,request:RiskEventStatusUpdate):
    try:return {"event":events.update_status(event_id,request.status)}
    except KeyError as exc:raise HTTPException(status_code=404,detail="Risk event not found") from exc

@router.post("/{event_id}/grounding")
def copilot_grounding(event_id:str):
    event=events.get(event_id)
    if not event:raise HTTPException(status_code=404,detail="Risk event not found")
    return {"event_id":event["event_id"],"dataset_id":event["dataset_id"],"event_type":event["event_type"],"severity":event["severity"],"status":event["status"],"metric":event["metric"],"observed_value":event["observed_value"],"threshold":event.get("threshold"),"exposure":event.get("exposure"),"evidence":event.get("evidence") or {},"read_only":True,"ai_mutable_fields":[]}

@router.post("/{event_id}/lifecycle/transition")
def transition_lifecycle(event_id:str,payload:dict):
    event=events.get(event_id)
    if not event: raise HTTPException(status_code=404,detail="Risk event not found")
    existing=lifecycle_store.find({"event_id":event_id},limit=1)
    base=RiskEventLifecycle(event_key=event["event_key"],severity=str(event.get("severity","LOW")),confidence=float(payload.get("confidence",0.0)),expected_financial_impact=float(event.get("exposure",0.0)),owner_id=payload.get("owner_id"),sla_deadline_utc=sla_deadline(str(event.get("severity","LOW"))),recurrence_count=int(payload.get("recurrence_count",0)))
    if existing:
        base=RiskEventLifecycle(event_key=str(existing[0]["event_key"]),status=LifecycleStatus(existing[0]["status"]),severity=str(existing[0].get("severity","LOW")),confidence=float(existing[0].get("confidence",0)),expected_financial_impact=float(existing[0].get("expected_financial_impact",0)),owner_id=existing[0].get("owner_id"),sla_deadline_utc=__import__("datetime").datetime.fromisoformat(existing[0]["sla_deadline_utc"]) if existing[0].get("sla_deadline_utc") else None,resolution_notes=existing[0].get("resolution_notes"),recurrence_count=int(existing[0].get("recurrence_count",0)))
    try: target=LifecycleStatus(str(payload["target_status"]).upper()); updated=transition(base,target)
    except (KeyError,ValueError) as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    document={"event_id":event_id,"event_key":updated.event_key,"status":updated.status.value,"severity":updated.severity,"confidence":updated.confidence,"expected_financial_impact":updated.expected_financial_impact,"owner_id":updated.owner_id,"sla_deadline_utc":updated.sla_deadline_utc.isoformat() if updated.sla_deadline_utc else None,"resolution_notes":updated.resolution_notes,"recurrence_count":updated.recurrence_count}
    if existing:lifecycle_store.update({"event_id":event_id},{"$set":document})
    else:lifecycle_store.insert(document)
    return {"event_id":event_id,"lifecycle":document,"contract":"risk-intelligence-v1"}
