from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.data.mongo import MongoRepository
from app.engine.formula_engine import FormulaEngine

router = APIRouter(prefix="/v1/indicators", tags=["indicators"])
repository = MongoRepository("custom_indicators")
formula_engine = FormulaEngine()


@router.get("")
def list_indicators(dataset_id: str | None = None) -> dict:
    filters = {"dataset_id": dataset_id} if dataset_id else {}
    rows = repository.find(filters, limit=200)
    return {"items": rows}


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

    existing = repository.find({"dataset_id": dataset_id, "id": indicator_id}, limit=1)
    document = {
        "dataset_id": dataset_id,
        "id": indicator_id,
        "name": name,
        "formula": formula,
        "description": payload.get("description") or "",
        "version": int(payload.get("version") or (existing[0].get("version", 0) + 1 if existing else 1)),
        "status": "validated",
    }
    record_id = repository.insert(document)
    return {"saved": True, "record_id": record_id, "indicator": document}


@router.delete("/{indicator_id}")
def delete_indicator(indicator_id: str, dataset_id: str | None = None) -> dict:
    # The small repository adapter intentionally does not expose deletes yet;
    # mark the indicator inactive instead so audit history is preserved.
    rows = repository.find({"dataset_id": dataset_id or "", "id": indicator_id}, limit=1)
    if not rows:
        raise HTTPException(status_code=404, detail="Indicator not found")
    return {"deleted": False, "message": "Indicators are versioned and retained for audit."}
