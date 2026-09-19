from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.data.mongo import MongoRepository
from app.engine.formula_engine import FormulaEngine

router = APIRouter(prefix="/v1/indicators", tags=["indicators"])
repository = MongoRepository("custom_indicators")
formula_engine = FormulaEngine()


def _latest(rows: list[dict]) -> list[dict]:
    latest: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (str(row.get("dataset_id") or ""), str(row.get("id") or ""))
        if not key[1]:
            continue
        current = latest.get(key)
        version = int(row.get("version") or 0)
        current_version = int(current.get("version") or 0) if current else -1
        if current is None or version >= current_version:
            latest[key] = row
    return sorted(latest.values(), key=lambda item: (str(item.get("name") or item.get("id")), str(item.get("id"))))


@router.get("")
def list_indicators(dataset_id: str | None = None, include_inactive: bool = False) -> dict:
    filters = {"dataset_id": dataset_id} if dataset_id else {}
    rows = repository.find(filters, limit=1000)
    if not include_inactive:
        rows = [row for row in rows if row.get("status", "active") != "archived"]
    return {"items": _latest(rows)}


@router.post("")
def save_indicator(payload: dict) -> dict:
    dataset_id = str(payload.get("dataset_id") or "")
    indicator_id = str(payload.get("id") or "").strip()
    name = str(payload.get("name") or indicator_id).strip()
    formula = str(payload.get("formula") or "").strip()
    if not indicator_id:
        raise HTTPException(status_code=422, detail=["id is required"])
    if not formula:
        raise HTTPException(status_code=422, detail=["formula is required"])
    errors = formula_engine.validate(formula)
    if errors:
        raise HTTPException(status_code=422, detail=errors)

    existing = _latest(repository.find({"dataset_id": dataset_id, "id": indicator_id}, limit=1000))
    current = existing[0] if existing else None
    next_version = int(current.get("version", 0) if current else 0) + 1
    now = datetime.now(timezone.utc).isoformat()
    document = {
        "dataset_id": dataset_id,
        "id": indicator_id,
        "name": name,
        "formula": formula,
        "description": payload.get("description") or "",
        "version": next_version,
        "status": "active",
        "created_by": payload.get("created_by") or "user",
        "updated_at": now,
        "audit_action": "created" if not current else "versioned",
    }
    record_id = repository.insert(document)
    return {"saved": True, "record_id": record_id, "indicator": document}


@router.post("/evaluate")
def evaluate_indicators(payload: dict) -> dict:
    facts = dict(payload.get("facts") or {})
    dataset_id = str(payload.get("dataset_id") or "")
    requested = payload.get("indicator_ids") or []
    rows = repository.find({"dataset_id": dataset_id}, limit=1000)
    indicators = _latest(rows)
    if requested:
        requested_set = {str(item) for item in requested}
        indicators = [item for item in indicators if str(item.get("id")) in requested_set]
    formulas = {str(item["id"]): str(item["formula"]) for item in indicators if item.get("formula")}
    if not formulas:
        return {"facts": facts, "values": {}, "trace": [], "indicators": []}
    try:
        result = formula_engine.evaluate(facts, formulas)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=[str(exc)])
    values = {key: result.get("facts", {}).get(key) for key in formulas}
    return {"facts": result.get("facts", facts), "values": values, "trace": result.get("trace", []), "indicators": indicators}


@router.post("/{indicator_id}/archive")
def archive_indicator(indicator_id: str, dataset_id: str | None = None, actor: str = "user") -> dict:
    rows = repository.find({"dataset_id": dataset_id or "", "id": indicator_id}, limit=1000)
    latest = _latest(rows)
    if not latest:
        raise HTTPException(status_code=404, detail="Indicator not found")
    current = latest[0]
    archived = dict(current)
    archived.pop("_id", None)
    archived["status"] = "archived"
    archived["audit_action"] = "archived"
    archived["archived_by"] = actor
    archived["updated_at"] = datetime.now(timezone.utc).isoformat()
    archived["version"] = int(current.get("version") or 0) + 1
    record_id = repository.insert(archived)
    return {"archived": True, "record_id": record_id, "indicator": archived}
