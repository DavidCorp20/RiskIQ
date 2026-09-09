from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.audit.decision_history import DecisionHistoryService

router = APIRouter(prefix="/v1/audit", tags=["audit"])
service = DecisionHistoryService()


@router.post("/decisions")
def record_decision(payload: dict) -> dict:
    decision = payload.get("decision", payload)
    actor = str(payload.get("actor", "system"))
    return service.record(decision, actor)


@router.get("/decisions")
def list_decisions(status: str | None = None) -> dict:
    entries = service.list(status)
    return {"count": len(entries), "entries": entries}


@router.post("/decisions/{decision_id}/outcome")
def resolve_decision(decision_id: str, payload: dict) -> dict:
    try:
        return service.resolve(decision_id, payload.get("outcome", payload))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Decision not found") from exc
