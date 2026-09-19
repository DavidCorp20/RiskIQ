from __future__ import annotations

import pytest

from app.market.correlation import RiskMarketCorrelationEngine
from app.market.models import EvidenceClassification, StatisticalEvidence
from app.market.providers import MarketDataProvider
from app.market.service import MarketContextService


class FakeMarketProvider(MarketDataProvider):
    async def fetch_indicators(self):
        from app.market.models import MarketIndicator

        return [
            MarketIndicator(
                symbol="NQ=F",
                value=24000,
                previous_value=23800,
                change_pct=0.8403,
                source="test",
            )
        ]


class FailingMarketProvider(MarketDataProvider):
    async def fetch_indicators(self):
        raise RuntimeError("provider down")


@pytest.mark.asyncio
async def test_market_context_normalizes_provider_contract():
    service = MarketContextService(
        market_providers=[FakeMarketProvider()],
        ttl_seconds=60,
    )

    result = await service.get_context()

    assert result["status"] == "available"
    assert "NQ=F" in result["market_indicators"]
    assert result["market_indicators"]["NQ=F"]["change_pct"] == pytest.approx(0.8403)


@pytest.mark.asyncio
async def test_market_context_is_partial_when_one_provider_fails():
    service = MarketContextService(
        market_providers=[FakeMarketProvider(), FailingMarketProvider()],
        ttl_seconds=60,
    )

    result = await service.get_context()

    assert result["status"] == "partial"
    assert result["market_indicators"]["NQ=F"]["value"] == 24000
    assert result["errors"]


@pytest.mark.asyncio
async def test_market_context_cache_hit():
    service = MarketContextService(
        market_providers=[FakeMarketProvider()],
        ttl_seconds=60,
    )

    await service.get_context()
    second = await service.get_context()

    assert second["cache"] == "hit"


def test_correlation_requires_formal_statistical_validation():
    engine = RiskMarketCorrelationEngine(alpha=0.05, min_sample_size=30)

    finding = engine.classify(
        portfolio_observation={"metric": "PAR30", "value": 0.12},
        market_observation={"symbol": "NQ=F", "change_pct": -2.1},
    )

    assert finding.classification == EvidenceClassification.POSSIBLE_EXPLANATION


def test_validated_correlation_is_not_causality():
    engine = RiskMarketCorrelationEngine(alpha=0.05, min_sample_size=30)

    finding = engine.classify(
        portfolio_observation={"metric": "PAR30", "value": 0.12},
        market_observation={"symbol": "NQ=F", "change_pct": -2.1},
        statistical_evidence=StatisticalEvidence(
            metric="PAR30",
            market_indicator="NQ=F",
            coefficient=-0.48,
            p_value=0.01,
            sample_size=48,
            method="pearson",
            validated=True,
        ),
    )

    assert finding.classification == EvidenceClassification.CORRELATED
    assert finding.causal_evidence is None


def test_causality_requires_explicit_validated_evidence():
    engine = RiskMarketCorrelationEngine()

    finding = engine.classify(
        portfolio_observation={"metric": "NPL", "value": 0.08},
        market_observation={"symbol": "FEDFUNDS", "value": 5.25},
        causal_evidence={
            "validated": True,
            "method": "approved_causal_inference_pipeline",
        },
    )

    assert finding.classification == EvidenceClassification.CAUSALITY_CONFIRMED
