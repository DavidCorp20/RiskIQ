from fastapi import APIRouter,HTTPException
from .stress_engine import StressEngine
from .profiles import REGIONAL_PROFILES
router=APIRouter(prefix="/v1/stress-testing",tags=["stress-testing"]);engine=StressEngine()
@router.get("/profiles")
def profiles():return {"profiles":REGIONAL_PROFILES}
@router.post("/run")
def run(payload:dict):
 try:return engine.run(payload.get("baseline") or {},str(payload.get("scenario") or "BASE"),payload.get("shocks"),payload.get("sensitivities"),payload.get("profile"))
 except (ValueError,TypeError) as exc:raise HTTPException(422,str(exc)) from exc
