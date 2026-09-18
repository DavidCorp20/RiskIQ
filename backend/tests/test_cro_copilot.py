from __future__ import annotations

import pytest\n\nfrom app.ai.copilot import RiskCopilotService
from app.analytics.risk_analytics import RiskAnalyticsService


def test_cro_evidence_calculates_par_dollar_impact_and_migration_stress() -> None:
    rows = [
        {"loan_id": "L1", "snapshot_date": "2026-08-31", "dpd": 35, "outstanding_principal": 1000, "segment": "A"},
        {"loan_id": "L1", "snapshot_date": "2026-09-30", "dpd": 95, "outstanding_principal": 900, "segment": "A"},
        {"loan_id": "L2", "snapshot_date": "2026-08-31", "dpd": 10, "outstanding_principal": 500, "segment": "B"},
        {"loan_id": "L2", "snapshot_date": "2026-09-30", "dpd": 65, "outstanding_principal": 450, "segment": "B"},
    ]

    analysis = RiskAnalyticsService().analyze(rows)
    evidence = analysis["cro_evidence"]

    assert evidence["exposure"]["total_balance"] == 1350
    assert evidence["par"]["par30"]["ratio"] == round(1350 / 1350, 4)
    assert evidence["exposure_impact"]["par30_balance"] == 1350
    assert evidence["exposure_impact"]["stress_if_30_to_89_migrates_to_90_plus"] == 450
    assert evidence["migration"]["available"] is True
    assert evidence["migration"]["early_to_hard"]["roll_rate_by_balance"] == 1.0


async @pytest.mark.asyncio\nasync def test_cro_copilot_adapts_to_question_and_does_not_claim_causality() -> None:
    risk = RiskAnalyticsService().analyze([
        {"loan_id": "L1", "snapshot_date": "2026-09-30", "dpd": 35, "outstanding_principal": 1000, "segment": "A"},
        {"loan_id": "L2", "snapshot_date": "2026-09-30", "dpd": 0, "outstanding_principal": 1000, "segment": "B"},
    ])

    result = await await RiskCopilotService().answer(
        "¿Qué debería revisar primero?",
        risk,
        drivers=risk["drivers"],
    )

    assert result["prompt_version"] == "cro-interactive-risk-analyst-v5"
    assert result["grounded"] is True
    answer = result["answer"]
    assert "**Situación de la cartera**" not in answer
    assert "**Deterioro y migración**" not in answer
    assert "**Concentraciones e hipótesis de trabajo**" not in answer
    assert "**Prioridades de gestión**" not in answer
    assert "causality" not in answer.lower()
    assert "como hecho observado" not in answer.lower()
    assert "como hipótesis a validar" not in answer.lower()
    assert "no es un forecast" not in answer.lower()
    assert "\n- " not in answer
    assert "\n1. " not in answer

    segment_result = RiskCopilotService().answer("Analiza el Segmento A", risk, drivers=risk["drivers"])
    assert segment_result["prompt_version"] == "cro-interactive-risk-analyst-v5"
    assert "Segmento A" in segment_result["answer"]
    assert "PAR30" in segment_result["answer"]

async @pytest.mark.asyncio\nasync def test_cro_copilot_explicitly_declares_insufficient_longitudinal_evidence() -> None:
    risk = RiskAnalyticsService().analyze([
        {"loan_id": "L1", "snapshot_date": "2026-09-30", "dpd": 35, "outstanding_principal": 1000, "segment": "A"},
    ])
    result = RiskCopilotService().answer("Analiza la migración", risk, drivers=risk["drivers"])
    assert result["prompt_version"] == "cro-interactive-risk-analyst-v4"
    assert "La evidencia es insuficiente" in result["answer"]
    assert "snapshots longitudinales" in result["answer"]
    assert "no es un forecast" not in result["answer"].lower()
    assert "como hecho observado" not in result["answer"].lower()
    assert "como hipótesis a validar" not in result["answer"].lower()
