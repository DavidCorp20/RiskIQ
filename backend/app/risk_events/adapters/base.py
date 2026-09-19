from __future__ import annotations

from typing import Any, Protocol

from app.risk_events.models import RiskAction


class RiskActionAdapter(Protocol):
    """Outbound Action Layer contract. RiskIQ remains the system of record."""

    async def dispatch(self, action: RiskAction | dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
        ...
