from __future__ import annotations
from copy import deepcopy
from typing import Any
REGIONAL_PROFILES: dict[str, dict[str, Any]] = {
    "LATAM_CONSERVATIVE":{"name":"LATAM Conservative","calibration_status":"scenario_preset","shocks":{"unemployment":1.0,"interest_rate":1.0,"inflation":1.0,"gdp":-1.0,"fx":5.0,"nasdaq_nq":-5.0}},
    "LATAM_SEVERE_INFLATION":{"name":"LATAM Severe Inflation","calibration_status":"scenario_preset","shocks":{"unemployment":3.0,"interest_rate":4.0,"inflation":6.0,"gdp":-3.0,"fx":20.0,"nasdaq_nq":-20.0}},
    "CUSTOM_CENTRAL_BANK":{"name":"Custom Central Bank","calibration_status":"user_supplied","shocks":{}},
}
def get_profile(name: str) -> dict[str, Any]:
    key=str(name or "").upper()
    if key not in REGIONAL_PROFILES: raise ValueError(f"Unknown macro profile: {key}")
    return deepcopy(REGIONAL_PROFILES[key])
