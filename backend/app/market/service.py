from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any

from app.market.models import MarketContext
from app.market.providers import (
    MacroEventProvider,
    MarketDataProvider,
    NullMacroEventProvider,
    NullMarketDataProvider,
    FredMacroIndicatorProvider,
    YahooNQMarketDataProvider,
)


class MarketContextService:
    """Normalizes external market/macro data into one RiskIQ contract.

    The service is best-effort and cached. External data can enrich analysis,
    but it never becomes the source of truth for deterministic credit metrics.
    """

    def __init__(
        self,
        market_providers: list[MarketDataProvider] | None = None,
        macro_provider: MacroEventProvider | None = None,
        ttl_seconds: int | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.cache_ttl_seconds = int(
            ttl_seconds or os.getenv("MARKET_CONTEXT_CACHE_TTL_SECONDS", "60")
        )
        self.timeout_seconds = float(
            timeout_seconds or os.getenv("MARKET_CONTEXT_TIMEOUT_SECONDS", "3")
        )
        self.market_providers = market_providers or self._default_market_providers()
        self.macro_provider = macro_provider or NullMacroEventProvider()
        self._cache: dict[str, Any] | None = None
        self._cache_at = 0.0
        self._lock = asyncio.Lock()

    @staticmethod
    def _default_market_providers() -> list[MarketDataProvider]:
        providers: list[MarketDataProvider] = [YahooNQMarketDataProvider()]
        if os.getenv("MARKET_FRED_API_KEY", "").strip():
            providers.append(FredMacroIndicatorProvider())
        else:
            providers.append(NullMarketDataProvider())
        return providers

    async def get_context(self) -> dict[str, Any]:
        now = asyncio.get_running_loop().time()
        if self._cache is not None and now - self._cache_at < self.cache_ttl_seconds:
            cached = dict(self._cache)
            cached["cache"] = "hit"
            return cached

        async with self._lock:
            now = asyncio.get_running_loop().time()
            if self._cache is not None and now - self._cache_at < self.cache_ttl_seconds:
                cached = dict(self._cache)
                cached["cache"] = "hit"
                return cached

            context = await self._fetch()
            self._cache = context
            self._cache_at = now
            return dict(context)

    async def _fetch(self) -> dict[str, Any]:
        enabled = os.getenv("MARKET_CONTEXT_ENABLED", "true").strip().lower() in {
            "1", "true", "yes", "on"
        }
        if not enabled:
            return MarketContext(
                as_of=datetime.now(timezone.utc).date().isoformat(),
                status="disabled",
                cache="miss",
                ttl_seconds=self.cache_ttl_seconds,
            ).model_dump()

        indicator_results = await asyncio.gather(
            *(provider.fetch_indicators() for provider in self.market_providers),
            return_exceptions=True,
        )
        macro_result = await asyncio.gather(
            self.macro_provider.fetch_events(),
            return_exceptions=True,
        )

        indicators = {}
        errors: list[str] = []
        for result in indicator_results:
            if isinstance(result, Exception):
                errors.append(f"market provider unavailable: {type(result).__name__}")
                continue
            for indicator in result:
                indicators[indicator.symbol] = indicator

        events = []
        macro = macro_result[0]
        if isinstance(macro, Exception):
            errors.append(f"macro event provider unavailable: {type(macro).__name__}")
        else:
            events = macro

        status = "available" if indicators or events else "unavailable"
        if errors and (indicators or events):
            status = "partial"

        normalized = MarketContext(
            as_of=datetime.now(timezone.utc).isoformat(),
            market_indicators=indicators,
            macro_events=events,
            status=status,
            errors=errors,
            cache="miss",
            ttl_seconds=self.cache_ttl_seconds,
        ).model_dump(mode="json")
        # Backward-compatible view for the existing Copilot/frontend contract.
        normalized["data"] = {
            "market_indicators": normalized["market_indicators"],
            "macro_events": normalized["macro_events"],
        }
        return normalized
