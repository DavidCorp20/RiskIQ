from __future__ import annotations

from copy import deepcopy
from unittest.mock import AsyncMock

import pytest

from app.risk_events.adapters.internal import InternalTaskAdapter
from app.risk_events.adapters.webhook import WebhookActionAdapter
from app.risk_events.models import ActionType, RiskAction


class FakeRepo:
    def __init__(self):
        self.rows = []

    def ensure_indexes(self):
        pass

    def ensure_unique_index(self, fields, *, name=None):
        pass

    def find(self, filters=None, limit=100):
        filters = filters or {}
        return [deepcopy(r) for r in self.rows if all(r.get(k) == v for k, v in filters.items())][:limit]

    def insert(self, document):
        self.rows.append(deepcopy(document))
        return str(len(self.rows))

    def update(self, filters, update):
        return True


def _action():
    return RiskAction(
        action_id="action-1",
        event_id="event-1",
        action_type=ActionType.ESCALATION,
        priority=1,
        owner="risk_committee",
        rationale="critical event",
        evidence={"x": 1},
    )


@pytest.mark.asyncio
async def test_internal_adapter_is_idempotent():
    repo = FakeRepo()
    adapter = InternalTaskAdapter(repo)
    event = {"event_id": "event-1", "dataset_id": "ds-1", "severity": "CRITICAL", "event_type": "DPD_SEVERITY"}
    first = await adapter.dispatch(_action(), event)
    second = await adapter.dispatch(_action(), event)
    assert first["created"] is True
    assert second["created"] is False
    assert len(repo.rows) == 1


@pytest.mark.asyncio
async def test_webhook_adapter_retries_and_signs(monkeypatch):
    adapter = WebhookActionAdapter("https://example.com/hook", "secret")
    responses = []

    class Response:
        def __init__(self, status_code):
            self.status_code = status_code
            self.headers = {}
        def raise_for_status(self):
            raise RuntimeError(f"http {self.status_code}")

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        async def post(self, url, content, headers):
            responses.append((url, content, headers))
            if len(responses) == 1:
                return Response(503)
            return Response(200)

    monkeypatch.setattr("app.risk_events.adapters.webhook.httpx.AsyncClient", lambda **kwargs: FakeClient())
    monkeypatch.setattr("app.risk_events.adapters.webhook.asyncio.sleep", AsyncMock())
    monkeypatch.setattr("app.risk_events.adapters.webhook.settings.riskiq_action_max_retries", 1)

    result = await adapter.dispatch(_action(), {"event_id": "event-1", "severity": "CRITICAL"})
    assert result["status_code"] == 200
    assert len(responses) == 2
    assert responses[0][2]["X-RiskIQ-Signature"].startswith("sha256=")
    assert responses[0][2]["Idempotency-Key"] == "action-1"
