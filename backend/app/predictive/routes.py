from fastapi import APIRouter,HTTPException
from typing import Any
from .pd_engine import PDEngine
from .survival_engine import SurvivalEngine
from .transition_engine import TransitionEngine
router=APIRouter(prefix="/v1/predictive",tags=["predictive"])
transition=TransitionEngine();pd=PDEngine();survival=SurvivalEngine()

@router.post("/transition")
def transition_matrix(payload:dict[str,Any]):
    try:return transition.build_matrix(payload.get("rows") or []).model_dump()
    except (ValueError,TypeError) as exc:raise HTTPException(422,str(exc))

@router.post("/pd")
def pd_ratings(payload:dict[str,Any]):
    try:
        matrix=transition.build_matrix(payload.get("rows") or [])
        horizon=int(payload.get("horizon_periods",1))
        return {"ratings":[x.model_dump() for x in pd.ratings(matrix,horizon)],"matrix":matrix.model_dump(),"validation":pd.validation_metrics(payload.get("scores") or [],payload.get("labels") or []) if payload.get("scores") else None}
    except (ValueError,TypeError) as exc:raise HTTPException(422,str(exc))

@router.post("/feature-importance")
def feature_importance(payload:dict):
    try:return {"items":pd.feature_importance(payload.get("rows") or [],payload.get("target","default"),payload.get("features"))}
    except (ValueError,TypeError) as exc:raise HTTPException(422,str(exc))

@router.post("/survival")
def survival_curve(payload:dict[str,Any]):
    try:return survival.kaplan_meier(payload.get("rows") or [],payload.get("event_field","default"),payload.get("duration_field","duration")).model_dump()
    except (ValueError,TypeError) as exc:raise HTTPException(422,str(exc))
