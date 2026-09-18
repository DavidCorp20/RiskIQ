from __future__ import annotations

from typing import Any

import pytest

from app.core.ai.provider import AIProvider
from app.services.ingestion.data_quality import DataQualityEngine
from app.services.ingestion.semantic_mapper import SemanticColumnMapper


class FakeProvider(AIProvider):
    async def generate(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        if context["column_name"] == "saldo_vencido_total":
            return {
                "target": "outstanding_principal",
                "confidence": 96,
                "reason": "La muestra contiene importes monetarios de saldo pendiente.",
            }
        return {"target": None, "confidence": 20, "reason": "Sin evidencia suficiente."}


def test_semantic_mapper_exact_and_normalized_match() -> None:
    rows = [
        {"Días de Mora": 12, "LOAN-ID": "L1", "Saldo Capital": 1000},
    ]

    result = SemanticColumnMapper().map_columns(rows)
    by_source = {item["source"]: item for item in result["columns"]}

    assert by_source["Días de Mora"]["target"] == "dpd"
    assert by_source["Días de Mora"]["confidence"] == 100.0
    assert by_source["LOAN-ID"]["target"] == "loan_id"
    assert by_source["Saldo Capital"]["target"] == "outstanding_principal"


def test_semantic_mapper_fuzzy_match() -> None:
    rows = [{"days_past_du": 15, "customer_numb": "C1"}]

    result = SemanticColumnMapper().map_columns(rows)
    by_source = {item["source"]: item for item in result["columns"]}

    assert by_source["days_past_du"]["target"] == "dpd"
    assert by_source["days_past_du"]["method"] == "fuzzy"
    assert by_source["days_past_du"]["confidence"] >= 85


@pytest.mark.asyncio
async def test_semantic_mapper_llm_fallback() -> None:
    rows = [{"saldo_vencido_total": 1250}, {"saldo_vencido_total": 950}]

    result = await SemanticColumnMapper(provider=FakeProvider()).map_columns_with_ai(rows)
    item = result["columns"][0]

    assert item["target"] == "outstanding_principal"
    assert item["method"] == "llm"
    assert item["confidence"] == 96


def test_quality_detects_financial_and_date_anomalies() -> None:
    rows = [
        {
            "customer_id": "C1",
            "loan_id": "L1",
            "outstanding_principal": -100,
            "dpd": -2,
            "origination_date": "2026-06-01",
            "payment_date": "2026-05-01",
            "due_date": "2026-05-15",
        }
    ]

    result = DataQualityEngine().assess(rows)
    codes = {issue["code"] for issue in result["issues"]}

    assert result["status"] == "blocked"
    assert "NEGATIVE_BALANCE" in codes
    assert "NEGATIVE_DPD" in codes
    assert "PAYMENT_BEFORE_ORIGINATION" in codes
    assert "DUE_BEFORE_ORIGINATION" in codes


def test_quality_detects_duplicate_snapshot_loan() -> None:
    rows = [
        {
            "customer_id": "C1",
            "loan_id": "L1",
            "snapshot_date": "2026-08-31",
            "outstanding_principal": 100,
        },
        {
            "customer_id": "C1",
            "loan_id": "L1",
            "snapshot_date": "2026-08-31",
            "outstanding_principal": 90,
        },
    ]

    result = DataQualityEngine().assess(rows)

    assert result["status"] == "blocked"
    assert result["checks"]["duplicate_snapshot_loan_keys"] == 1
    assert any(issue["code"] == "DUPLICATE_SNAPSHOT_LOAN" for issue in result["issues"])


def test_quality_allows_longitudinal_loan_history() -> None:
    rows = [
        {
            "customer_id": "C1",
            "loan_id": "L1",
            "snapshot_date": "2026-07-31",
            "outstanding_principal": 100,
        },
        {
            "customer_id": "C1",
            "loan_id": "L1",
            "snapshot_date": "2026-08-31",
            "outstanding_principal": 90,
        },
        {
            "customer_id": "C1",
            "loan_id": "L1",
            "snapshot_date": "2026-09-30",
            "outstanding_principal": 80,
        },
    ]

    result = DataQualityEngine().assess(rows)

    assert result["status"] == "passed"
    assert result["checks"]["duplicate_snapshot_loan_keys"] == 0


def test_quality_detects_invalid_numeric_type() -> None:
    rows = [
        {
            "customer_id": "C1",
            "loan_id": "L1",
            "outstanding_principal": "not-a-number",
        }
    ]

    result = DataQualityEngine().assess(rows)
    codes = {issue["code"] for issue in result["issues"]}

    assert "INVALID_NUMBER_OUTSTANDING_PRINCIPAL" in codes
    assert result["quality_score"] < 100


def test_quality_reports_five_model_readiness() -> None:
    rows = [
        {
            "customer_id": "C1",
            "loan_id": "L1",
            "snapshot_date": "2026-08-31",
            "origination_date": "2026-01-01",
            "outstanding_principal": 100,
            "dpd": 15,
            "segment": "retail",
        }
    ]

    result = DataQualityEngine().assess(rows)

    assert all(result["analysis_readiness"][name]["ready"] for name in (
        "Portfolio Health",
        "Delinquency Analysis",
        "Concentration Analysis",
        "Vintage Analysis",
        "Migration / Roll Rate",
    ))
