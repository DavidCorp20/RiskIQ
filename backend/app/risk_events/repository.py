from __future__ import annotations
from copy import deepcopy
from datetime import datetime,timezone
from typing import Any,Protocol
from pymongo.errors import DuplicateKeyError
from app.data.mongo import MongoRepository
from app.integrations.freshservice import FreshserviceClient
from .models import ActionStatus,RiskAction,RiskEvent,RiskEventStatus
class Store(Protocol):
    def ensure_indexes(self)->None: ...
    def ensure_unique_index(self,fields:list[tuple[str,int]],*,name:str|None=None)->None: ...
    def find(self,filters:dict[str,Any]|None=None,limit:int=100)->list[dict[str,Any]]: ...
    def insert(self,document:dict[str,Any])->str: ...
    def update(self,filters:dict[str,Any],update:dict[str,Any])->bool: ...
class RiskEventRepository:
    def __init__(self,store:Store|None=None):self.store=store or MongoRepository("risk_events");self.ready=False
    def _ensure(self):
        if self.ready:return
        self.store.ensure_indexes();self.store.ensure_unique_index([("event_key",1)],name="uniq_risk_event_key");self.ready=True
    def create_if_absent(self,event:RiskEvent):
        self._ensure(); existing=self.store.find({"event_key":event.event_key},limit=1)
        if existing:return existing[0]
        doc=event.model_dump(mode="json")
        try:self.store.insert(doc)
        except DuplicateKeyError:
            existing=self.store.find({"event_key":event.event_key},limit=1)
            if existing:return existing[0]
            raise
        return doc
    def get(self,event_id:str):self._ensure();rows=self.store.find({"event_id":event_id},limit=1);return rows[0] if rows else None
    def list(self,dataset_id:str|None=None,status:str|None=None,limit:int=500):
        self._ensure();f={};
        if dataset_id:f["dataset_id"]=dataset_id
        if status:f["status"]=status
        return sorted(self.store.find(f,limit=max(1,min(limit,1000))),key=lambda x:str(x.get("created_at") or ""),reverse=True)
    def update_status(self,event_id:str,status:RiskEventStatus):
        row=self.get(event_id)
        if not row:raise KeyError(event_id)
        now=datetime.now(timezone.utc).isoformat();self.store.update({"event_id":event_id},{"$set":{"status":status.value,"updated_at":now}});row=deepcopy(row);row.update(status=status.value,updated_at=now);return row
class RiskActionRepository:
    def __init__(self,store:Store|None=None):self.store=store or MongoRepository("risk_actions");self.ready=False
    def _ensure(self):
        if self.ready:return
        self.store.ensure_indexes();self.store.ensure_unique_index([("event_id",1),("action_type",1)],name="uniq_risk_action_event_type");self.ready=True
    def create_if_absent(self,action:RiskAction):
        self._ensure();existing=self.store.find({"event_id":action.event_id,"action_type":action.action_type.value},limit=1)
        if existing:return existing[0]
        doc=action.model_dump(mode="json")
        try:self.store.insert(doc)
        except DuplicateKeyError:
            existing=self.store.find({"event_id":action.event_id,"action_type":action.action_type.value},limit=1)
            if existing:return existing[0]
            raise
        return doc
    def get(self,action_id:str):self._ensure();rows=self.store.find({"action_id":action_id},limit=1);return rows[0] if rows else None
    def list(self,event_id:str|None=None,status:str|None=None,limit:int=500):
        self._ensure();f={};
        if event_id:f["event_id"]=event_id
        if status:f["status"]=status
        return sorted(self.store.find(f,limit=max(1,min(limit,1000))),key=lambda x:str(x.get("created_at") or ""),reverse=True)
    def update_status(self,action_id:str,status:ActionStatus):
        row=self.get(action_id)
        if not row:raise KeyError(action_id)
        now=datetime.now(timezone.utc).isoformat();self.store.update({"action_id":action_id},{"$set":{"status":status.value,"updated_at":now}});row=deepcopy(row);row.update(status=status.value,updated_at=now);return row
class FreshserviceRiskActionAdapter:
    """Execution-only adapter; RiskIQ event/action state remains authoritative."""
    def __init__(self,client:FreshserviceClient|None=None,sync:Store|None=None):self.client=client or FreshserviceClient();self.sync=sync or MongoRepository("risk_event_freshservice_sync");self.ready=False
    def _ensure(self):
        if self.ready:return
        self.sync.ensure_indexes();self.sync.ensure_unique_index([("action_id",1)],name="uniq_risk_action_freshservice");self.ready=True
    async def sync_action(self,action:dict[str,Any],event:dict[str,Any]):
        self._ensure()
        if not self.client.enabled:return {"enabled":False,"action_id":action["action_id"]}
        current=self.sync.find({"action_id":action["action_id"]},limit=1)
        payload={"subject":f"RiskIQ | {action['action_type']} | {event['event_type']} | {event['event_id']}","description":f"<p><strong>RiskIQ Risk Event</strong></p><p>Event: {event['event_id']}</p><p>Severity: {event['severity']}</p><p>Metric: {event['metric']}</p><p>Observed: {event['observed_value']}</p><p>Threshold: {event.get('threshold')}</p><p>Exposure: {event.get('exposure')}</p><p>Rationale: {action['rationale']}</p>","priority":int(action["priority"]),"status":2,"source":2,"tags":["riskiq","risk-event",str(action["action_type"]).lower()],"custom_fields":{"riskiq_event_id":event["event_id"],"riskiq_action_id":action["action_id"],"riskiq_severity":event["severity"]}}
        if current and current[0].get("freshservice_ticket_id"):ticket=await self.client.update_ticket(current[0]["freshservice_ticket_id"],payload);ticket_id=current[0]["freshservice_ticket_id"]
        else:
            ticket=await self.client.create_ticket(payload);ticket_id=ticket.get("id")
            if not ticket_id:raise RuntimeError("Freshservice did not return a ticket id")
        record={"action_id":action["action_id"],"event_id":event["event_id"],"freshservice_ticket_id":ticket_id,"last_payload":payload,"last_response":ticket,"updated_at":datetime.now(timezone.utc).isoformat()}
        if current:self.sync.update({"action_id":action["action_id"]},{"$set":record})
        else:self.sync.insert({**record,"created_at":record["updated_at"]})
        return {"enabled":True,"action_id":action["action_id"],"freshservice_ticket_id":ticket_id}
