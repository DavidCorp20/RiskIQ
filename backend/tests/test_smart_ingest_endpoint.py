from __future__ import annotations

import io
from typing import Any

from fastapi.testclient import TestClient

from app.core.ai.provider import AIProvider
from app.main import app
import app.api.v1.endpoints.smart_ingest as smart_ingest


class FakeProvider(AIProvider):
    async def generate(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "target": "outstanding_principal",
            "confidence": 96,
            "reason": "La muestra representa saldos pendientes.",
        }


def test_smart_ingest_endpoint_returns_mapping_quality_and_readiness(monkeypatch) -> None:
    monkeypatch.setattr(smart_ingest, "get_ai_provider", lambda: FakeProvider())

    csv = (
        "cliente,credito,fecha_corte,fecha_desembolso,dias_mora,segmento,saldo_vencido_total\n"
        "C1,L1,2026-08-31,2026-01-01,15,retail,1000\n"
        "C2,L2,2026-08-31,2026-02-01,3,micro,500\n"
    )

    response = TestClient(app).post(
        "/api/v1/data/smart-ingest",
        files={"file": ("portfolio.csv", io.BytesIO(csv.encode()), "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["contract_version"] == "smart-ingest-v1"
    assert body["persistence"]["persisted"] is False
    assert body["quality"]["status"] == "passed"
    assert body["mapping"]["acceptance_threshold"] == 85.0
    assert any(item["target"] == "outstanding_principal" for item in body["mapping"]["accepted"])
    assert "Portfolio Health" in body["risk_model_readiness"]["ready_models"]
    assert "Migration / Roll Rate" in body["risk_model_readiness"]["ready_models"]
