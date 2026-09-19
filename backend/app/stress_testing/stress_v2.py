from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

from .profiles import get_profile

GUARDRAILS = {
    "minimum_sample_size": 12,
    "minimum_abs_correlation": 0.50,
    "maximum_p_value": 0.05,
}


def _validated(contract: dict[str, Any] | None) -> bool:
    if not contract:
        return False
    return (
        bool(contract.get("validated"))
        and abs(float(contract.get("coefficient", 0.0))) >= GUARDRAILS["minimum_abs_correlation"]
        and float(contract.get("p_value", 1.0)) < GUARDRAILS["maximum_p_value"]
        and int(contract.get("sample_size", 0)) >= GUARDRAILS["minimum_sample_size"]
    )


def run_macro_stress(
    *,
    base_pd: float,
    base_lgd: float,
    base_ead: float,
    profile: str = "LATAM_CONSERVATIVE",
    shocks: dict[str, float] | None = None,
    elasticities: dict[str, dict[str, float]] | None = None,
    validation: dict[str, dict[str, Any]] | None = None,
    capital_base: float | None = None,
) -> dict[str, Any]:
    selected = get_profile(profile)
    effective_shocks = {**selected.get("shocks", {}), **(shocks or {})}
    elasticities = elasticities or {}
    validation = validation or {}

    def adjust(base: float, metric: str) -> tuple[float, list[dict[str, Any]]]:
        total = 0.0
        evidence = []
        for macro, shock in effective_shocks.items():
            contract = validation.get(f"{metric}:{macro}") or validation.get(macro)
            if not _validated(contract):
                continue
            elasticity = float(elasticities.get(metric, {}).get(macro, 0.0))
            delta = base * elasticity * (float(shock) / 100.0)
            total += delta
            evidence.append({
                "metric": metric,
                "macro": macro,
                "shock": float(shock),
                "elasticity": elasticity,
                "coefficient": contract.get("coefficient"),
                "p_value": contract.get("p_value"),
                "sample_size": contract.get("sample_size"),
                "validated": True,
            })
        return max(0.0, total), evidence

    pd_delta, pd_evidence = adjust(base_pd, "pd")
    lgd_delta, lgd_evidence = adjust(base_lgd, "lgd")
    ead_delta, ead_evidence = adjust(base_ead, "ead")

    stressed_pd = min(1.0, max(0.0, base_pd + pd_delta))
    stressed_lgd = min(1.0, max(0.0, base_lgd + lgd_delta))
    stressed_ead = max(0.0, base_ead + ead_delta)

    baseline_el = base_pd * base_lgd * base_ead
    stressed_el = stressed_pd * stressed_lgd * stressed_ead
    incremental_loss = max(0.0, stressed_el - baseline_el)
    capital_impact = incremental_loss if capital_base is None else incremental_loss / max(float(capital_base), 1e-12)

    payload = {
        "contract": "risk-intelligence-v1",
        "scenario": selected["name"],
        "profile": profile.upper(),
        "calibration_status": selected.get("calibration_status"),
        "shocks": effective_shocks,
        "baseline": {"pd": base_pd, "lgd": base_lgd, "ead": base_ead, "expected_loss": baseline_el},
        "stressed": {"pd": stressed_pd, "lgd": stressed_lgd, "ead": stressed_ead, "expected_loss": stressed_el},
        "impact": {
            "incremental_expected_loss": incremental_loss,
            "capital_impact": capital_impact,
            "capital_impact_type": "ratio" if capital_base is not None else "absolute_loss",
        },
        "evidence": pd_evidence + lgd_evidence + ead_evidence,
        "guardrail": GUARDRAILS,
        "causality_confirmed": False,
        "methodology": "macro-shock-elasticity-pd-lgd-ead-el-v1",
    }
    payload["run_id"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return payload
