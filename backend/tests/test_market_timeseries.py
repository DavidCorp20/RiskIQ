from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.market.correlation import RiskMarketCorrelationEngine
from app.market.models import (
    EvidenceClassification,
    HistoricalSeries,
    StatisticalEvidence,
    TimeSeriesPoint,
)
from app.market.statistics import CorrelationMethod, TimeSeriesStatistics
from app.market.timeseries import AlignmentPolicy, SeriesFrequency, TimeSeriesAligner


def _series(name: str, values: list[float], start: date = date(2025, 1, 1)) -> HistoricalSeries:
    return HistoricalSeries(
        name=name,
        source="test",
        frequency="daily",
        points=[
            TimeSeriesPoint(date=start + timedelta(days=index), value=value)
            for index, value in enumerate(values)
        ],
    )


def test_daily_alignment_respects_tolerance_and_previous_preference():
    portfolio = _series("PAR30", [10.0], date(2025, 1, 10))
    market = HistoricalSeries(
        name="NQ=F",
        source="test",
        points=[
            TimeSeriesPoint(date=date(2025, 1, 9), value=100.0),
            TimeSeriesPoint(date=date(2025, 1, 11), value=110.0),
        ],
    )

    aligned = TimeSeriesAligner().align(
        portfolio,
        market,
        AlignmentPolicy(
            frequency=SeriesFrequency.DAILY,
            tolerance_days=2,
            prefer_previous=True,
        ),
    )

    assert len(aligned) == 1
    assert aligned[0].market_date == date(2025, 1, 9)
    assert aligned[0].market_value == 100.0


def test_monthly_alignment_normalizes_calendar_days():
    portfolio = _series("PAR30", [10.0], date(2025, 1, 15))
    market = HistoricalSeries(
        name="FEDFUNDS",
        source="test",
        points=[
            TimeSeriesPoint(date=date(2025, 1, 31), value=5.25),
        ],
    )

    aligned = TimeSeriesAligner().align(
        portfolio,
        market,
        AlignmentPolicy(frequency=SeriesFrequency.MONTHLY, tolerance_days=0),
    )

    assert len(aligned) == 1
    assert aligned[0].market_value == 5.25


def test_transformations():
    stats = TimeSeriesStatistics(min_sample_size=12)

    assert stats.transform([10, 12, 15], "level") == [10.0, 12.0, 15.0]
    assert stats.transform([10, 12, 15], "change") == [2.0, 3.0]
    assert stats.transform([10, 12, 15], "pct_change") == pytest.approx([0.2, 0.25])
    assert stats.transform([10, 12, 15], "return") == pytest.approx([0.2, 0.25])


def test_statistics_rejects_sample_below_minimum():
    stats = TimeSeriesStatistics(min_sample_size=12)

    evidence = stats.correlate(
        metric="PAR30",
        market_indicator="NQ=F",
        x=list(range(11)),
        y=list(range(11)),
    )

    assert evidence.validated is False
    assert evidence.sample_size == 11
    assert "Insufficient sample" in (evidence.validation_notes or "")


def test_statistics_validates_pearson_and_spearman():
    stats = TimeSeriesStatistics(min_sample_size=12, alpha=0.05)
    x = list(range(1, 25))
    y = [value * 2.0 for value in x]

    pearson = stats.correlate(
        metric="PAR30",
        market_indicator="NQ=F",
        x=x,
        y=y,
        method=CorrelationMethod.PEARSON,
    )
    spearman = stats.correlate(
        metric="PAR30",
        market_indicator="NQ=F",
        x=x,
        y=y,
        method=CorrelationMethod.SPEARMAN,
    )

    assert pearson.validated is True
    assert spearman.validated is True
    assert pearson.coefficient == pytest.approx(1.0)
    assert spearman.coefficient == pytest.approx(1.0)
    assert pearson.p_value is not None and pearson.p_value <= 0.05


def test_correlation_engine_aligns_transforms_and_computes_statistics():
    portfolio = _series("PAR30", [10 + index * 0.5 for index in range(24)])
    market = _series("NQ=F", [100 - index * 1.5 for index in range(24)])

    engine = RiskMarketCorrelationEngine(min_sample_size=12, alpha=0.05)
    evidence = engine.analyze_series(
        portfolio=portfolio,
        market=market,
        policy=AlignmentPolicy(frequency=SeriesFrequency.DAILY, tolerance_days=0),
        portfolio_transformation="change",
        market_transformation="return",
        methods=[CorrelationMethod.PEARSON],
    )

    assert len(evidence) == 1
    assert evidence[0].sample_size == 23
    assert evidence[0].method == "pearson"


def test_transition_never_assigns_causality():
    engine = RiskMarketCorrelationEngine(min_sample_size=12)

    evidence = StatisticalEvidence(
        metric="PAR90",
        market_indicator="NQ=F",
        coefficient=-0.7,
        p_value=0.001,
        sample_size=24,
        method="pearson",
        validated=True,
    )

    assert (
        engine.transition_state(evidence, has_external_observation=True)
        == EvidenceClassification.CORRELATED
    )


def test_classifier_requires_explicit_external_causal_validation():
    engine = RiskMarketCorrelationEngine(min_sample_size=12)

    evidence = StatisticalEvidence(
        metric="PAR90",
        market_indicator="NQ=F",
        coefficient=-0.7,
        p_value=0.001,
        sample_size=24,
        method="pearson",
        validated=True,
    )

    finding = engine.classify(
        portfolio_observation={"metric": "PAR90", "value": 0.08},
        market_observation={"symbol": "NQ=F"},
        statistical_evidence=evidence,
    )
    assert finding.classification == EvidenceClassification.CORRELATED

    causal = engine.classify(
        portfolio_observation={"metric": "PAR90", "value": 0.08},
        market_observation={"symbol": "NQ=F"},
        statistical_evidence=evidence,
        causal_evidence={"validated": True, "method": "external_validation"},
    )
    assert causal.classification == EvidenceClassification.CAUSALITY_CONFIRMED
