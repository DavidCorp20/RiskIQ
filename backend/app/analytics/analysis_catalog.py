from __future__ import annotations

from typing import Any


INDICATORS: list[dict[str, Any]] = [
    {"id": "exposure", "name": "Exposición", "category": "portfolio", "status": "core", "requires": ["outstanding_principal"]},
    {"id": "active_accounts", "name": "Créditos activos", "category": "portfolio", "status": "core", "requires": ["loan_id"]},
    {"id": "par7", "name": "PAR7", "category": "delinquency", "status": "core", "requires": ["dpd", "outstanding_principal"]},
    {"id": "par30", "name": "PAR30", "category": "delinquency", "status": "core", "requires": ["dpd", "outstanding_principal"]},
    {"id": "par60", "name": "PAR60", "category": "delinquency", "status": "core", "requires": ["dpd", "outstanding_principal"]},
    {"id": "par90", "name": "PAR90", "category": "delinquency", "status": "core", "requires": ["dpd", "outstanding_principal"]},
    {"id": "concentration_hhi", "name": "HHI de concentración", "category": "concentration", "status": "core", "requires": ["segment", "outstanding_principal"]},
    {"id": "vintage_par30", "name": "Vintage PAR30", "category": "vintage", "status": "core", "requires": ["origination_date", "dpd", "outstanding_principal"]},
    {"id": "roll_rate", "name": "Roll Rate", "category": "migration", "status": "core", "requires": ["loan_id", "snapshot_date", "dpd", "outstanding_principal"]},
    {"id": "expected_loss", "name": "Pérdida esperada", "category": "advanced_risk", "status": "planned", "requires": ["pd", "lgd", "ead"]},
]

ANALYSIS_MODELS: list[dict[str, Any]] = [
    {
        "id": "portfolio_health",
        "name": "Portfolio Health",
        "category": "core",
        "status": "available",
        "question": "¿Cómo está la cartera y cuál es su principal foco de riesgo?",
        "indicators": ["exposure", "active_accounts", "par30", "par60", "par90", "concentration_hhi"],
        "requires": ["dpd", "outstanding_principal"],
    },
    {
        "id": "delinquency",
        "name": "Delinquency Analysis",
        "category": "core",
        "status": "available",
        "question": "¿Cómo está distribuida la mora y dónde se concentra?",
        "indicators": ["par7", "par30", "par60", "par90"],
        "requires": ["dpd", "outstanding_principal"],
    },
    {
        "id": "concentration",
        "name": "Concentration Analysis",
        "category": "core",
        "status": "available",
        "question": "¿Dónde se concentra la exposición y el deterioro?",
        "indicators": ["concentration_hhi", "par30"],
        "requires": ["segment", "outstanding_principal", "dpd"],
    },
    {
        "id": "vintage",
        "name": "Vintage Analysis",
        "category": "core",
        "status": "available",
        "question": "¿Qué cohortes de originación presentan peor desempeño?",
        "indicators": ["vintage_par30"],
        "requires": ["origination_date", "dpd", "outstanding_principal"],
    },
    {
        "id": "migration",
        "name": "Migration / Roll Rate",
        "category": "core",
        "status": "available",
        "question": "¿Cómo se mueve la cartera entre estados de mora?",
        "indicators": ["roll_rate"],
        "requires": ["loan_id", "snapshot_date", "dpd", "outstanding_principal"],
    },
    {
        "id": "what_if",
        "name": "What-if Scenario",
        "category": "scenario",
        "status": "available",
        "question": "¿Qué cambia si modifico una variable o supuesto?",
        "indicators": [],
        "requires": ["outstanding_principal", "dpd"],
    },
    {
        "id": "stress_testing",
        "name": "Stress Testing",
        "category": "scenario",
        "status": "planned",
        "question": "¿Cómo respondería la cartera bajo un escenario adverso?",
        "indicators": ["par30", "par90"],
        "requires": ["dpd", "outstanding_principal", "historical_snapshots"],
    },
    {
        "id": "expected_loss",
        "name": "Expected Loss",
        "category": "advanced_risk",
        "status": "planned",
        "question": "¿Cuál es la pérdida esperada bajo la metodología seleccionada?",
        "indicators": ["expected_loss"],
        "requires": ["pd", "lgd", "ead"],
    },
    {
        "id": "monte_carlo",
        "name": "Monte Carlo",
        "category": "advanced_risk",
        "status": "planned",
        "question": "¿Cuál es la distribución posible de resultados bajo incertidumbre?",
        "indicators": [],
        "requires": ["historical_data", "scenario_parameters"],
    },
]


def _missing(requires: list[str], available_fields: set[str]) -> list[str]:
    return [field for field in requires if field not in available_fields]


def readiness(item: dict[str, Any], available_fields: list[str] | None = None) -> dict[str, Any]:
    fields = set(available_fields or [])
    missing = _missing(list(item.get("requires") or []), fields) if available_fields is not None else []
    return {
        "ready": not missing and item.get("status") in {"available", "core"},
        "missing_fields": missing,
        "status": item.get("status"),
    }


def catalog(available_fields: list[str] | None = None) -> dict[str, Any]:
    return {
        "version": "analysis-catalog-v1",
        "indicators": [dict(item, readiness=readiness(item, available_fields)) for item in INDICATORS],
        "models": [dict(item, readiness=readiness(item, available_fields)) for item in ANALYSIS_MODELS],
        "principle": "Indicators are calculations; models are methodologies; policies are decision logic.",
    }
