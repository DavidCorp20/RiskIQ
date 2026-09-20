from __future__ import annotations
from typing import Any
from fastapi import APIRouter, HTTPException
from app.api.schemas import DecisionRule
from app.domain.core_pipeline import RiskCorePipeline
router=APIRouter(prefix="/v1/core",tags=["product-core"]); pipeline=RiskCorePipeline()
@router.post("/run")
def run_core(payload:dict[str,Any])->dict[str,Any]:
    try:
        rules=[DecisionRule.model_validate(x) for x in (payload.get("rules") or [])]
        return pipeline.run(payload.get("rows") or [],rules,dataset_id=payload.get("dataset_id"),snapshot_id=payload.get("snapshot_id"),actor=str(payload.get("actor") or "system")).model_dump(mode="json")
    except (ValueError,TypeError) as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
