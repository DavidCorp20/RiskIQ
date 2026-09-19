from __future__ import annotations
from hashlib import sha256
import json
from typing import Any

SCENARIOS={"BASE":{},"ADVERSE":{"unemployment":2.0,"interest_rate":1.5,"inflation":2.0,"gdp":-1.5,"fx":10.0,"nasdaq_nq":-10.0},"SEVERE_STRESS":{"unemployment":4.0,"interest_rate":3.0,"inflation":4.0,"gdp":-3.0,"fx":20.0,"nasdaq_nq":-25.0}}
MACRO_KEYS=("unemployment","interest_rate","inflation","gdp","fx","nasdaq_nq")

class StressEngine:
    def run(self, baseline:dict[str,float], scenario:str, shocks:dict[str,float]|None=None, sensitivities:dict[str,dict[str,dict[str,Any]]]|None=None)->dict[str,Any]:
        name=scenario.upper()
        if name not in SCENARIOS: raise ValueError("scenario must be BASE, ADVERSE or SEVERE_STRESS")
        effective={**SCENARIOS[name],**(shocks or {})}
        sensitivities=sensitivities or {}
        projected=dict(baseline)
        evidence=[]
        for metric,market_map in sensitivities.items():
            if metric not in baseline: continue
            total_delta=0.0
            for macro,contract in market_map.items():
                if macro not in effective: continue
                if not self._validated(contract): continue
                elasticity=float(contract.get("elasticity",0.0))
                total_delta += float(baseline[metric]) * elasticity * (effective[macro]/100.0)
                evidence.append({"metric":metric,"macro":macro,"coefficient":contract.get("coefficient"),"p_value":contract.get("p_value"),"sample_size":contract.get("sample_size"),"elasticity":elasticity,"shock":effective[macro],"classification":"CORRELATED"})
            projected[metric]=round(max(0.0,baseline[metric]+total_delta),8)
        payload={"scenario":name,"shocks":effective,"baseline":baseline,"projected":projected,"evidence":evidence,"methodology":"deterministic-sensitivity-v1","causality_confirmed":False}
        payload["run_id"]=sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        return payload

    @staticmethod
    def _validated(contract:dict[str,Any])->bool:
        return bool(contract.get("validated")) and abs(float(contract.get("coefficient",0)))>=0.50 and float(contract.get("p_value",1))<0.05 and int(contract.get("sample_size",0))>=12
