from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from typing import Any

import httpx

from app.config import settings
from app.risk_events.models import RiskAction


class WebhookActionAdapter:
    """HTTPS adapter with canonical JSON + HMAC signing and bounded retries."""

    def __init__(self, url: str | None = None, secret: str | None = None) -> None:
        self.url = (url or settings.riskiq_action_webhook_url).strip()
        self.secret = secret or settings.riskiq_action_webhook_secret
        self.timeout = httpx.Timeout(settings.riskiq_action_timeout_seconds)

    @staticmethod
    def _canonical(payload: dict[str, Any]) -> bytes:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")

    def _signature(self, body: bytes) -> str:
        return hmac.new(self.secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    async def dispatch(self, action: RiskAction | dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
        if not self.url or not self.secret:
            return {"enabled": False, "adapter": "WEBHOOK", "reason": "not_configured"}

        action_dict = action.model_dump(mode="json") if isinstance(action, RiskAction) else dict(action)
        payload = {"schema": "riskiq-risk-action-v1", "action": action_dict, "event": dict(event)}
        body = self._canonical(payload)
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "RiskIQ-ActionAdapter/1.0",
            "X-RiskIQ-Signature": f"sha256={self._signature(body)}",
            "X-RiskIQ-Action-Id": str(action_dict["action_id"]),
            "Idempotency-Key": str(action_dict["action_id"]),
        }

        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
            for attempt in range(settings.riskiq_action_max_retries + 1):
                try:
                    response = await client.post(self.url, content=body, headers=headers)
                    if response.status_code < 300:
                        return {
                            "enabled": True,
                            "adapter": "WEBHOOK",
                            "status_code": response.status_code,
                            "action_id": action_dict["action_id"],
                        }
                    if response.status_code not in {408, 425, 429, 500, 502, 503, 504}:
                        response.raise_for_status()
                    if attempt >= settings.riskiq_action_max_retries:
                        response.raise_for_status()
                    retry_after = response.headers.get("Retry-After")
                    try:
                        delay = float(retry_after) if retry_after else settings.riskiq_action_retry_backoff_seconds * (2 ** attempt)
                    except ValueError:
                        delay = settings.riskiq_action_retry_backoff_seconds * (2 ** attempt)
                    await asyncio.sleep(min(delay, settings.riskiq_action_max_retry_delay_seconds))
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    last_error = exc
                    if attempt >= settings.riskiq_action_max_retries:
                        raise
                    await asyncio.sleep(min(
                        settings.riskiq_action_retry_backoff_seconds * (2 ** attempt),
                        settings.riskiq_action_max_retry_delay_seconds,
                    ))
        if last_error:
            raise last_error
        raise RuntimeError("RiskIQ webhook dispatch failed")
