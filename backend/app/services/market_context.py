from __future__ import annotations

"""Backward-compatible facade for the RiskIQ Market Intelligence Layer.

New code should depend on app.market.* contracts. This facade keeps the
previous MarketContextProvider import and parser contract stable.
"""

import os
from typing import Any

from app.market.providers import FredMacroIndicatorProvider, YahooNQMarketDataProvider
from app.market.service import MarketContextService


class MarketContextProvider(MarketContextService):
    """Compatibility facade for the previous MarketContextProvider API."""

    def __init__(self, ttl_seconds: int | None = None, timeout_seconds: float | None = None) -> None:
        timeout = timeout_seconds or 3.0
        self.enabled = os.getenv("MARKET_CONTEXT_ENABLED", "true").strip().lower() in {
            "1", "true", "yes", "on"
        }
        self.nq_symbol = os.getenv("MARKET_NQ_SYMBOL", "NQ=F")
        self._nq_provider = YahooNQMarketDataProvider(
            symbol=self.nq_symbol,
            timeout_seconds=timeout,
        )
        super().__init__(
            market_providers=[
                self._nq_provider,
                FredMacroIndicatorProvider(timeout_seconds=timeout),
            ],
            ttl_seconds=ttl_seconds,
            timeout_seconds=timeout_seconds,
        )

    def _parse_yahoo(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        parsed = self._nq_provider._parse(payload)
        return parsed.model_dump(mode="json") if parsed else None
