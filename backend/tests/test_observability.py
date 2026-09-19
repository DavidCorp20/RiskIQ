from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.observability import RiskIQObservabilityMiddleware


def test_observability_adds_request_headers():
    app = FastAPI()
    app.add_middleware(RiskIQObservabilityMiddleware)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    response = TestClient(app).get("/health", headers={"X-Request-ID": "test-request"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request"
    assert "X-RiskIQ-Latency-MS" in response.headers
    assert "X-RiskIQ-Memory-Delta-KB" in response.headers
