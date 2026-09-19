from __future__ import annotations

import pytest

from app.ai.copilot import RiskCopilotService
from app.analytics.risk_analytics import RiskAnalyticsService
from app.core.ai.provider import AIProvider


class FakeProvider(AIProvider):
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def generate(self, prompt: str, context: dict) -> dict:
        self.calls.append((prompt, context))
        return {"answer": "Respuesta de prueba."}


def _risk() -> dict:
    return RiskAnalyticsService().analyze(
        [
            {"loan_id": "L1", "snapshot_date": "2026-09-30", "dpd": 35, "outstanding_principal": 1000, "segment": "A"},
            {"loan_id": "L2", "snapshot_date": "2026-09-30", "dpd": 0, "outstanding_principal": 1000, "segment": "B"},
        ]
    )


@pytest.mark.asyncio
async def test_conversational_mode_does_not_send_risk_evidence() -> None:
    provider = FakeProvider()
    result = await RiskCopilotService(provider).answer(
        "Hola, buenos días",
        _risk(),
        conversation=[{"role": "user", "content": "Hola"}],
    )

    assert result["conversation_mode"] == "conversational"
    assert result["prompt_version"] == "cro-dual-mode-market-correlation-v2"
    assert result["grounded"] is True
    _, context = provider.calls[0]
    assert "EVIDENCE_JSON" not in context
    assert "FACTS" not in context
    assert context["CURRENT_QUESTION"] == "Hola, buenos días"


@pytest.mark.asyncio
async def test_analytical_mode_sends_deterministic_evidence_and_history() -> None:
    provider = FakeProvider()
    result = await RiskCopilotService(provider).answer(
        "Analiza el PAR30 de la cartera",
        _risk(),
        conversation=[
            {"role": "user", "content": "¿Qué está pasando?"},
            {"role": "assistant", "content": "Hay deterioro temprano."},
        ],
    )

    assert result["conversation_mode"] == "analytical"
    assert result["prompt_version"] == "cro-dual-mode-v1"
    _, context = provider.calls[0]
    assert context["EVIDENCE_JSON"]
    assert context["FACTS"]
    assert len(context["CONVERSATION"]) == 2
    assert context["CURRENT_QUESTION"] == "Analiza el PAR30 de la cartera"
    assert "EWS_JSON" in context


@pytest.mark.asyncio
async def test_provider_failure_keeps_deterministic_fallback() -> None:
    class FailingProvider(AIProvider):
        async def generate(self, prompt: str, context: dict) -> dict:
            raise RuntimeError("provider unavailable")

    result = await RiskCopilotService(FailingProvider()).answer(
        "Analiza la migración",
        _risk(),
    )

    assert result["conversation_mode"] == "analytical"
    assert result["grounded"] is True
    assert result["answer"]


@pytest.mark.asyncio
async def test_conversation_is_preserved_in_service_context() -> None:
    provider = FakeProvider()
    service = RiskCopilotService(provider)
    history = [{"role": "user", "content": "Hola"}]

    await service.answer("¿Qué es PAR30?", _risk(), conversation=history)

    context = service.build_context(_risk(), conversation=history)
    assert context["conversation"] == history


@pytest.mark.asyncio
async def test_ews_is_injected_only_in_analytical_mode() -> None:
    provider = FakeProvider()
    risk = _risk()
    risk["ews"] = {
        "available": True,
        "methodology": "portfolio-ews-v1",
        "predictive_probability": False,
        "portfolio": {
            "high_ews_loans": 1,
            "high_ews_exposure": 750.0,
            "high_ews_exposure_share": 0.375,
        },
        "top_alerts": [{"loan_id": "L1", "score": 82.0, "band": "critical"}],
        "guardrails": {"deterministic": True, "weighted_ratios": True, "predictive_probability": False},
    }

    result = await RiskCopilotService(provider).answer("¿Qué alertas tempranas debería revisar?", risk)

    assert result["conversation_mode"] == "analytical"
    _, context = provider.calls[0]
    assert context["EWS_JSON"]["available"] is True
    assert context["EWS_JSON"]["predictive_probability"] is False
    assert "alertas" in context["EWS_JSON"]["top_alerts"][0] or context["EWS_JSON"]["top_alerts"][0]["loan_id"] == "L1"


@pytest.mark.asyncio
async def test_conversational_mode_does_not_send_ews() -> None:
    provider = FakeProvider()
    risk = _risk()
    risk["ews"] = {"available": True, "portfolio": {"high_ews_loans": 1}}

    result = await RiskCopilotService(provider).answer("Hola, ¿cómo estás?", risk)

    assert result["conversation_mode"] == "conversational"
    _, context = provider.calls[0]
    assert "EWS_JSON" not in context


@pytest.mark.asyncio
async def test_market_correlation_evidence_is_injected_only_in_analytical_mode() -> None:
    provider = FakeProvider()
    evidence = [{
        "portfolio_metric": "par30",
        "market_metric": "nasdaq_100",
        "segment": "microcredito",
        "transformation": "change",
        "method": "spearman",
        "sample_size": 36,
        "coefficient": -0.61,
        "p_value": 0.0001,
        "classification": "CORRELATED",
        "direction": "negative",
        "evidence_rule": "n >= 12 AND |r| >= 0.50 AND p < 0.05",
    }]
    risk = _risk()
    risk["market_correlation"] = evidence

    result = await RiskCopilotService(provider).answer(
        "Analiza si el PAR30 está correlacionado con Nasdaq-100",
        risk,
    )

    assert result["conversation_mode"] == "analytical"
    assert result["market_correlation_evidence"] == evidence
    _, context = provider.calls[0]
    assert context["MARKET_CORRELATION_EVIDENCE"][0]["coefficient"] == -0.61
    assert context["MARKET_CORRELATION_EVIDENCE"][0]["p_value"] == 0.0001
    assert context["MARKET_CORRELATION_EVIDENCE"][0]["sample_size"] == 36
    assert "CAUSALITY_CONFIRMED" not in context["MARKET_CORRELATION_EVIDENCE"][0]["classification"]


@pytest.mark.asyncio
async def test_market_correlation_is_not_sent_in_conversational_mode() -> None:
    provider = FakeProvider()
    risk = _risk()
    risk["market_correlation"] = [{
        "portfolio_metric": "par30",
        "market_metric": "nasdaq_100",
        "method": "spearman",
        "sample_size": 36,
        "coefficient": -0.61,
        "p_value": 0.0001,
        "classification": "CORRELATED",
    }]

    result = await RiskCopilotService(provider).answer("Hola", risk)

    assert result["conversation_mode"] == "conversational"
    _, context = provider.calls[0]
    assert "MARKET_CORRELATION_EVIDENCE" not in context


@pytest.mark.asyncio
async def test_market_correlation_fallback_preserves_three_sections() -> None:
    class FailingProvider(AIProvider):
        async def generate(self, prompt: str, context: dict) -> dict:
            raise RuntimeError("provider unavailable")

    risk = _risk()
    risk["market_correlation"] = [{
        "portfolio_metric": "par30",
        "market_metric": "nasdaq_100",
        "method": "spearman",
        "sample_size": 36,
        "coefficient": -0.61,
        "p_value": 0.0001,
        "classification": "CORRELATED",
        "direction": "negative",
    }]

    result = await RiskCopilotService(FailingProvider()).answer(
        "Analiza la relación entre PAR30 y Nasdaq-100",
        risk,
    )

    assert result["provider"] == "market_correlation_evidence_mode"
    assert "Hechos Observados y Estadísticos" in result["answer"]
    assert "Interpretación Contextual" in result["answer"]
    assert "Limitaciones Metodológicas" in result["answer"]
    assert "causalidad" in result["answer"].lower()
