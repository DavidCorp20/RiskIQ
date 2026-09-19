from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.integrations.freshservice import ComplianceAutomationService, FreshserviceClient


@pytest.mark.asyncio
async def test_freshservice_client_retries_transient_503(monkeypatch):
    client = FreshserviceClient()
    client.api_key = "test"
    client.base_url = "https://example.freshservice.com"

    class Response:
        status_code = 503
        headers = {}
        content = b'{"message":"temporary"}'

        def raise_for_status(self):
            raise RuntimeError("503")

    fake_response = Response()

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def request(self, *args, **kwargs):
            return fake_response

    monkeypatch.setattr(client, "_client", lambda: FakeClient())
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(
        "app.integrations.freshservice.settings.freshservice_max_retries",
        1,
    )

    with pytest.raises(RuntimeError, match="503"):
        await client._request("GET", "/api/v2/tickets")


def test_compliance_event_is_idempotent(monkeypatch):
    service = ComplianceAutomationService()
    service.outbox = type(
        "Repo",
        (),
        {
            "find": lambda self, filters, limit=1: [{"event_key": filters["event_key"]}],
            "insert": lambda self, document: None,
            "ensure_indexes": lambda self: None,
            "_collection": type("Collection", (), {"create_index": lambda *args, **kwargs: None})(),
        },
    )()

    event = {"policy_id": "policy-1", "version": 2, "to": "DEPLOYED"}
    first = service.enqueue(event_type="policy_transition", event=event)
    second = service.enqueue(event_type="policy_transition", event=event)

    assert first["event_key"] == second["event_key"]


def test_webhook_secret_is_not_accepted_without_configuration(monkeypatch):
    monkeypatch.setattr(
        "app.integrations.freshservice.settings.freshservice_webhook_secret",
        "",
    )
    assert ComplianceAutomationService.verify_webhook_secret("anything") is False
