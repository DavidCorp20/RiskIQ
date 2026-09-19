from fastapi import APIRouter,HTTPException
from .stress_engine import StressEngine
from .stress_v2 import run_macro_stress
from .profiles import REGIONAL_PROFILES
router=APIRouter(prefix="/v1/stress-testing",tags=["stress-testing"]);engine=StressEngine()
@router.get("/profiles")
def profiles():return {"profiles":REGIONAL_PROFILES}
@router.post("/run")
def run(payload:dict):
 try:return engine.run(payload.get("baseline") or {},str(payload.get("scenario") or "BASE"),payload.get("shocks"),payload.get("sensitivities"),payload.get("profile"))
 except (ValueError,TypeError) as exc:raise HTTPException(422,str(exc)) from exc

@router.post("/macro-v2")
def macro_stress_v2(payload:dict):
    try:
        return run_macro_stress(base_pd=float(payload["base_pd"]),base_lgd=float(payload["base_lgd"]),base_ead=float(payload["base_ead"]),profile=str(payload.get("profile","LATAM_CONSERVATIVE")),shocks=payload.get("shocks"),elasticities=payload.get("elasticities"),validation=payload.get("validation"),capital_base=payload.get("capital_base"))
    except (KeyError,TypeError,ValueError) as exc:
        raise HTTPException(422,str(exc))
