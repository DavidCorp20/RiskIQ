from __future__ import annotations

from typing import Any

from app.config import settings
from app.risk_events.repository import FreshserviceRiskActionAdapter
from app.risk_events.models import RiskAction

from .base import RiskActionAdapter
from .email import EmailNotificationAdapter
from .internal import InternalTaskAdapter
from .webhook import WebhookActionAdapter


class _FreshserviceAdapter:
    def __init__(self) -> None:
        self.adapter = FreshserviceRiskActionAdapter()

    async def dispatch(self, action: RiskAction | dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
        row = action.model_dump(mode="json") if isinstance(action, RiskAction) else dict(action)
        return await self.adapter.sync_action(row, event)


class ActionAdapterFactory:
    """Selects the outbound Action Layer without coupling domain logic to a vendor."""

    @staticmethod
    def create(channel: str | None = None) -> RiskActionAdapter:
        selected = (channel or settings.riskiq_action_adapter).strip().upper()
        if selected == "WEBHOOK":
            return WebhookActionAdapter()
        if selected == "EMAIL":
            return EmailNotificationAdapter()
        if selected == "INTERNAL":
            return InternalTaskAdapter()
        if selected == "FRESHSERVICE":
            return _FreshserviceAdapter()
        raise ValueError(f"Unsupported RiskIQ action adapter: {selected}")

    @staticmethod
    def configured() -> str:
        channel = settings.riskiq_action_adapter.strip().upper()
        if channel == "FRESHSERVICE" and not settings.freshservice_enabled:
            return "INTERNAL"
        return channel
