from __future__ import annotations

"""Backward-compatible facade for the RiskIQ Market Intelligence Layer.

New code should depend on MarketContextService and provider contracts under
app.market. The legacy import remains available to avoid breaking Copilot
integrations already deployed.
"""

from app.market.providers import YahooNQMarketDataProvider, FredMacroIndicatorProvider
from app.market.service import MarketContextService


class MarketContextProvider(MarketContextService):
    """Compatibility alias for the previous MarketContextProvider API."""

    def __init__(self, ttl_seconds: int | None = None, timeout_seconds: float | None = None) -> None:
        super().__init__(
            market_providers=[
                YahooNQMarketDataProvider(timeout_seconds=timeout_seconds or 3.0),
                FredMacroIndicatorProvider(timeout_seconds=timeout_seconds or 3.0),
            ],
            ttl_seconds=ttl_seconds,
            timeout_seconds=timeout_seconds,
        )
