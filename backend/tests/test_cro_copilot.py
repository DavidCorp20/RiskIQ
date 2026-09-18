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
    assert result["prompt_version"] == "cro-dual-mode-v1"
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
