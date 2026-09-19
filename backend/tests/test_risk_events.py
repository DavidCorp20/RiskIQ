from copy import deepcopy

import pytest

from app.risk_events.action_engine import ActionEngine
from app.risk_events.event_engine import RiskEventEngine
from app.risk_events.models import ActionType, RiskEventStatus
from app.risk_events.repository import FreshserviceRiskActionAdapter, RiskEventRepository


def _ews():
    return [{"loan_id":"L-1","snapshot_date":"2026-09-19","score":82.0,"band":"critical","signals":[{"code":"DPD_SEVERITY","severity":"critical","value":95,"points":25}],"features":{"loan_id":"L-1","snapshot_date":"2026-09-19","current_balance":12000,"current_dpd":95}}]


class FakeStore:
    def __init__(self): self.rows=[]
    def ensure_indexes(self): pass
    def ensure_unique_index(self, fields, *, name=None): pass
    def find(self, filters=None, limit=100):
        filters=filters or {}
        rows=[r for r in self.rows if all(r.get(k)==v for k,v in filters.items())]
        return deepcopy(rows[:limit])
    def insert(self, document): self.rows.append(deepcopy(document)); return str(len(self.rows))
    def update(self, filters, update):
        changed=False
        for row in self.rows:
            if all(row.get(k)==v for k,v in filters.items()):
                for k,v in (update.get("$set") or {}).items(): row[k]=deepcopy(v)
                changed=True
        return changed


class FakeFreshservice:
    enabled=True
    def __init__(self): self.created=0; self.updated=0
    async def create_ticket(self, ticket): self.created+=1; return {"id":123,"subject":ticket["subject"]}
    async def update_ticket(self, ticket_id, ticket): self.updated+=1; return {"id":ticket_id,"subject":ticket["subject"]}


def test_event_detection_is_deterministic():
    a=RiskEventEngine().detect("ds-1",_ews(),"snap-1")[0]
    b=RiskEventEngine().detect("ds-1",_ews(),"snap-1")[0]
    assert a.event_id==b.event_id and a.event_key==b.event_key


def test_repository_is_idempotent_for_same_event():
    store=FakeStore(); repo=RiskEventRepository(store=store); event=RiskEventEngine().detect("ds-1",_ews(),"snap-1")[0]
    first=repo.create_if_absent(event); second=repo.create_if_absent(event)
    assert first["event_id"]==second["event_id"] and len(store.rows)==1


def test_event_evidence_cannot_be_reassigned():
    event=RiskEventEngine().detect("ds-1",_ews(),"snap-1")[0]; original=deepcopy(event.evidence)
    with pytest.raises(Exception): event.evidence={}
    assert event.evidence==original


def test_action_engine_is_deterministic():
    event=RiskEventEngine().detect("ds-1",_ews(),"snap-1")[0]
    action=ActionEngine().create_action(event)
    assert action.action_type==ActionType.ESCALATION and action.priority==1 and action.event_id==event.event_id


def test_lifecycle_status_contract():
    assert RiskEventEngine().detect("ds-1",_ews(),"snap-1")[0].status==RiskEventStatus.OPEN


@pytest.mark.asyncio
async def test_freshservice_adapter_creates_once_then_updates_same_ticket():
    client=FakeFreshservice(); sync=FakeStore(); adapter=FreshserviceRiskActionAdapter(client=client,sync=sync)
    event=RiskEventEngine().detect("ds-1",_ews(),"snap-1")[0]; action=ActionEngine().create_action(event)
    a=await adapter.sync_action(action.model_dump(mode="json"),event.model_dump(mode="json"))
    b=await adapter.sync_action(action.model_dump(mode="json"),event.model_dump(mode="json"))
    assert a["freshservice_ticket_id"]==b["freshservice_ticket_id"]==123
    assert client.created==1 and client.updated==1 and len(sync.rows)==1
