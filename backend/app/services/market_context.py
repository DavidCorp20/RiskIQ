from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any

import httpx


class MarketContextProvider:
    """Best-effort external market context with short-lived in-memory caching.

    External context is advisory only. RiskIQ deterministic evidence remains the
    source of truth for all credit-risk metrics and decisions.
    """

    def __init__(self, ttl_seconds: int | None = None, timeout_seconds: float | None = None) -> None:
        self.cache_ttl_seconds = int(ttl_seconds or os.getenv("MARKET_CONTEXT_CACHE_TTL_SECONDS", "60"))
        self.timeout_seconds = float(timeout_seconds or os.getenv("MARKET_CONTEXT_TIMEOUT_SECONDS", "3"))
        self.nq_symbol = os.getenv("MARKET_NQ_SYMBOL", "NQ=F")
        self.enabled = os.getenv("MARKET_CONTEXT_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
        self.nq_url = os.getenv(
            "MARKET_NQ_URL",
            "https://query1.finance.yahoo.com/v8/finance/chart/NQ=F?range=1d&interval=5m",
        )
        self._cache: dict[str, Any] | None = None
        self._cache_at = 0.0
        self._lock = asyncio.Lock()

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
            context = await self._fetch_context()
            self._cache = context
            self._cache_at = now
            return dict(context)

    async def _fetch_context(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "status": "unavailable",
            "source": "Macro/NQ Futures",
            "as_of": datetime.now(timezone.utc).isoformat(),
            "ttl_seconds": self.cache_ttl_seconds,
            "cache": "miss",
            "data": {},
            "errors": [],
        }
        if not self.enabled:
            result["status"] = "disabled"
            return result

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(self.nq_url, headers={"User-Agent": "RiskIQ/1.0"})
                response.raise_for_status()
                payload = response.json()
            quote = self._parse_yahoo(payload)
            if quote:
                result["data"]["nq_futures"] = quote
                result["status"] = "available"
            else:
                result["errors"].append("NQ futures provider returned no usable quote")
        except Exception as exc:
            result["errors"].append(f"NQ provider unavailable: {type(exc).__name__}")
        return result

    def _parse_yahoo(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        chart = payload.get("chart") if isinstance(payload, dict) else None
        rows = chart.get("result") if isinstance(chart, dict) else None
        meta = rows[0].get("meta") if isinstance(rows, list) and rows else None
        if not isinstance(meta, dict):
            return None

        price = meta.get("regularMarketPrice")
        previous = meta.get("previousClose")
        if not isinstance(price, (int, float)):
            return None

        change_pct = None
        if isinstance(previous, (int, float)) and previous:
            change_pct = round(((price - previous) / previous) * 100, 4)

        timestamp = meta.get("regularMarketTime")
        as_of = (
            datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
            if isinstance(timestamp, (int, float))
            else None
        )
        return {
            "symbol": meta.get("symbol") or self.nq_symbol,
            "price": float(price),
            "previous_close": float(previous) if isinstance(previous, (int, float)) else None,
            "change_pct": change_pct,
            "as_of": as_of,
            "source": "Yahoo Finance / NQ Futures",
        }
