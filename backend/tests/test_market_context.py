import pytest

from app.services.market_context import MarketContextProvider


@pytest.mark.asyncio
async def test_market_context_disabled_does_not_call_external(monkeypatch):
    monkeypatch.setenv("MARKET_CONTEXT_ENABLED", "false")
    provider = MarketContextProvider()
    result = await provider.get_context()

    assert result["status"] == "disabled"
    assert result["data"] == {}
    assert result["source"] == "Macro/NQ Futures"


@pytest.mark.asyncio
async def test_market_context_cache_reuses_result(monkeypatch):
    monkeypatch.setenv("MARKET_CONTEXT_ENABLED", "false")
    provider = MarketContextProvider(ttl_seconds=60)

    first = await provider.get_context()
    second = await provider.get_context()

    assert first["status"] == "disabled"
    assert second["cache"] == "hit"


@pytest.mark.asyncio
async def test_market_context_nq_parser():
    provider = MarketContextProvider()
    payload = {
        "chart": {
            "result": [{
                "meta": {
                    "symbol": "NQ=F",
                    "regularMarketPrice": 24000,
                    "previousClose": 23800,
                    "regularMarketTime": 1760000000,
                }
            }]
        }
    }

    quote = provider._parse_yahoo(payload)

    assert quote is not None
    assert quote["symbol"] == "NQ=F"
    assert quote["price"] == 24000.0
    assert quote["change_pct"] == pytest.approx(0.8403, rel=1e-3)
