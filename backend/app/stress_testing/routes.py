from fastapi import APIRouter,HTTPException
from .stress_engine import StressEngine
router=APIRouter(prefix="/v1/stress-testing",tags=["stress-testing"])
engine=StressEngine()
@router.post("/run")
def run(payload:dict):
    try:return engine.run(payload.get("baseline") or {},str(payload.get("scenario") or "BASE"),payload.get("shocks"),payload.get("sensitivities"))
    except (ValueError,TypeError) as exc:raise HTTPException(422,str(exc))
