from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.market.models import MacroEvent, MarketIndicator


class MarketDataProvider(ABC):
    @abstractmethod
    async def fetch_indicators(self) -> list[MarketIndicator]:
        """Return normalized market indicators. Provider-specific payloads stay inside the adapter."""

    async def fetch_historical_series(self, *, range: str = "2y", interval: str = "1mo") -> list[dict[str, Any]]:
        """Return normalized historical points when the provider supports history."""
        return []


class MacroEventProvider(ABC):
    @abstractmethod
    async def fetch_events(self) -> list[MacroEvent]:
        """Return normalized macro events. Provider-specific payloads stay inside the adapter."""


class NullMarketDataProvider(MarketDataProvider):
    async def fetch_indicators(self) -> list[MarketIndicator]:
        return []


class NullMacroEventProvider(MacroEventProvider):
    async def fetch_events(self) -> list[MacroEvent]:
        return []


class YahooNQMarketDataProvider(MarketDataProvider):
    """Minimal Yahoo Finance adapter for NQ futures.

    This adapter is deliberately isolated so Yahoo can be replaced without
    changing RiskIQ's domain/service layer.
    """

    def __init__(
        self,
        url: str | None = None,
        symbol: str | None = None,
        timeout_seconds: float = 3.0,
    ) -> None:
        self.symbol = symbol or os.getenv("MARKET_NQ_SYMBOL", "NQ=F")
        self.url = url or os.getenv(
            "MARKET_NQ_URL",
            "https://query1.finance.yahoo.com/v8/finance/chart/NQ=F?range=1d&interval=5m",
        )
        self.timeout_seconds = timeout_seconds

    async def fetch_indicators(self) -> list[MarketIndicator]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(self.url, headers={"User-Agent": "RiskIQ/1.0"})
            response.raise_for_status()
            payload = response.json()

        quote = self._parse(payload)
        return [quote] if quote else []

    async def fetch_historical_series(self, *, range: str = "2y", interval: str = "1mo") -> list[dict[str, Any]]:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{self.symbol}?range={range}&interval={interval}"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(url, headers={"User-Agent": "RiskIQ/1.0"})
            response.raise_for_status()
            payload = response.json()

        chart = payload.get("chart") if isinstance(payload, dict) else None
        results = chart.get("result") if isinstance(chart, dict) else None
        if not isinstance(results, list) or not results:
            return []
        result = results[0]
        timestamps = result.get("timestamp") or []
        quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        closes = quote.get("close") or []
        points: list[dict[str, Any]] = []
        from datetime import datetime, timezone
        for timestamp, close in zip(timestamps, closes):
            if close is None:
                continue
            try:
                numeric = float(close)
                observed = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).date().isoformat()
            except (TypeError, ValueError, OverflowError):
                continue
            points.append({"date": observed, "value": numeric})
        return points

    def _parse(self, payload: dict[str, Any]) -> MarketIndicator | None:
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
        observed_at = str(timestamp) if timestamp is not None else None

        return MarketIndicator(
            symbol=str(meta.get("symbol") or self.symbol),
            value=float(price),
            previous_value=float(previous) if isinstance(previous, (int, float)) else None,
            change_pct=change_pct,
            unit="index_points",
            observed_at=observed_at,
            source="Yahoo Finance / NQ Futures",
        )


class FredMacroIndicatorProvider(MarketDataProvider):
    """FRED adapter for latest observations such as FEDFUNDS/CPIAUCSL/UNRATE."""

    def __init__(
        self,
        api_key: str | None = None,
        series: list[str] | None = None,
        url: str | None = None,
        timeout_seconds: float = 3.0,
    ) -> None:
        self.api_key = (api_key or os.getenv("MARKET_FRED_API_KEY", "")).strip()
        self.series = series or [
            item.strip()
            for item in os.getenv("MARKET_FRED_SERIES", "FEDFUNDS,CPIAUCSL,UNRATE").split(",")
            if item.strip()
        ]
        self.url = url or os.getenv(
            "MARKET_FRED_URL",
            "https://api.stlouisfed.org/fred/series/observations",
        )
        self.timeout_seconds = timeout_seconds

    async def fetch_indicators(self) -> list[MarketIndicator]:
        if not self.api_key:
            return []

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            results: list[MarketIndicator] = []
            for series_id in self.series:
                response = await client.get(
                    self.url,
                    params={
                        "series_id": series_id,
                        "api_key": self.api_key,
                        "file_type": "json",
                        "sort_order": "desc",
                        "limit": 1,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                observations = payload.get("observations") if isinstance(payload, dict) else None
                if not observations:
                    continue
                observation = observations[0]
                value = observation.get("value")
                if value in (None, "."):
                    continue
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    continue
                results.append(
                    MarketIndicator(
                        symbol=series_id,
                        value=numeric,
                        observed_at=observation.get("date"),
                        source="FRED",
                    )
                )
            return results
