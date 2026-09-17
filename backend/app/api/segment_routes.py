from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.data.persistence import PortfolioPersistenceService

router = APIRouter(prefix="/v1/datasets", tags=["segments"])
persistence = PortfolioPersistenceService()


def _require(dataset_id: str) -> None:
    if not persistence.datasets.find({"dataset_id": dataset_id}, limit=1):
        raise HTTPException(status_code=404, detail="Dataset not found")


def _matches(row: dict[str, Any], condition: dict[str, Any]) -> bool:
    field = str(condition.get("field") or "")
    if not field:
        return True
    value = row.get(field)
    operator = str(condition.get("operator") or "=")
    target = condition.get("value")
    if operator == "is_empty":
        return value is None or str(value).strip() == ""
    if operator == "is_not_empty":
        return value is not None and str(value).strip() != ""
    if operator == "contains":
        return str(target or "").lower() in str(value or "").lower()
    try:
        left, right = float(value), float(target)
    except (TypeError, ValueError):
        left, right = str(value or ""), str(target or "")
    return {"=": left == right, "!=": left != right, ">": left > right, ">=": left >= right, "<": left < right, "<=": left <= right}.get(operator, False)


def _latest(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dated = [r for r in rows if any(r.get(k) not in (None, "") for k in ("snapshot_date", "snapshot_month", "as_of_date"))]
    if dated:
        def key(r: dict[str, Any]) -> str:
            return next(str(r[k])[:10] for k in ("snapshot_date", "snapshot_month", "as_of_date") if r.get(k) not in (None, ""))
        latest_date = max(key(r) for r in dated)
        rows = [r for r in rows if any(str(r.get(k))[:10] == latest_date for k in ("snapshot_date", "snapshot_month", "as_of_date") if r.get(k) not in (None, ""))]
    by_loan: dict[str, dict[str, Any]] = {}
    for row in rows:
        loan_id = str(row.get("loan_id") or row.get("id") or "").strip()
        if loan_id: by_loan[loan_id] = row
    return list(by_loan.values()) if by_loan else rows


def _preview(rows: list[dict[str, Any]], conditions: list[dict[str, Any]]) -> dict[str, Any]:
    selected = [r for r in _latest(rows) if all(_matches(r, c) for c in conditions)]
    balance_key = next((k for k in ("outstanding_principal", "outstanding_balance", "balance") if any(r.get(k) not in (None, "") for r in selected)), "")
    exposure = sum(float(r.get(balance_key) or 0) for r in selected) if balance_key else 0
    bad30 = sum(float(r.get(balance_key) or 0) for r in selected if float(r.get("dpd") or r.get("days_past_due") or 0) >= 30) if balance_key else 0
    bad90 = sum(float(r.get(balance_key) or 0) for r in selected if float(r.get("dpd") or r.get("days_past_due") or 0) >= 90) if balance_key else 0
    return {"rows": len(selected), "exposure": round(exposure, 2), "par30": round(bad30 / exposure, 4) if exposure else 0, "par90": round(bad90 / exposure, 4) if exposure else 0, "balance_field": balance_key}


@router.get("/{dataset_id}/segments")
def list_segments(dataset_id: str) -> dict[str, Any]:
    _require(dataset_id)
    rows = persistence.dataset_mappings.find({"dataset_id": dataset_id}, limit=1000)
    segments = [r for r in rows if r.get("record_type") == "segment" and r.get("active", True)]
    return {"dataset_id": dataset_id, "segments": segments}


@router.post("/{dataset_id}/segments")
def save_segment(dataset_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    _require(dataset_id)
    name = str(payload.get("name") or "").strip()
    conditions = payload.get("conditions") or []
    if not name or not isinstance(conditions, list):
        raise HTTPException(status_code=400, detail="Segment name and conditions are required")
    rows = persistence.portfolio_records.find({"dataset_id": dataset_id}, limit=100000)
    preview = _preview(rows, conditions)
    existing = persistence.dataset_mappings.find({"dataset_id": dataset_id, "record_type": "segment", "name": name}, limit=1)
    document = {"dataset_id": dataset_id, "record_type": "segment", "name": name, "conditions": conditions, "preview": preview, "active": True}
    if existing:
        persistence.dataset_mappings.update({"dataset_id": dataset_id, "record_type": "segment", "name": name}, {"$set": document})
        return {"saved": True, "updated": True, "segment": document}
    persistence.dataset_mappings.insert(document)
    return {"saved": True, "updated": False, "segment": document}


@router.post("/{dataset_id}/segments/preview")
def preview_segment(dataset_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    _require(dataset_id)
    rows = persistence.portfolio_records.find({"dataset_id": dataset_id}, limit=100000)
    return {"dataset_id": dataset_id, "conditions": payload.get("conditions") or [], "preview": _preview(rows, payload.get("conditions") or [])}


@router.delete("/{dataset_id}/segments/{name}")
def archive_segment(dataset_id: str, name: str) -> dict[str, Any]:
    _require(dataset_id)
    updated = persistence.dataset_mappings.update({"dataset_id": dataset_id, "record_type": "segment", "name": name}, {"$set": {"active": False}})
    return {"deleted": updated, "name": name}
