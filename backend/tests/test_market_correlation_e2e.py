from __future__ import annotations

from datetime import date, timedelta

from app.analytics.risk_analytics import RiskAnalyticsService
from app.market.correlation import RiskMarketCorrelationEngine
from app.market.models import HistoricalSeries, TimeSeriesPoint


def _series(name: str, values: list[float]) -> HistoricalSeries:
    start = date(2023, 1, 31)
    return HistoricalSeries(
        name=name,
        source="test",
        frequency="monthly",
        points=[
            TimeSeriesPoint(
                date=start + timedelta(days=30 * index),
                value=value,
            )
            for index, value in enumerate(values)
        ],
    )


def test_correlation_engine_produces_statistical_evidence() -> None:
    engine = RiskMarketCorrelationEngine(min_sample_size=12)
    evidence = engine.analyze_series(
        portfolio=_series("par30", [0.01 + index * 0.001 for index in range(18)]),
        market=_series("NQ=F", [100 + index * 2 for index in range(18)]),
        portfolio_transformation="change",
        market_transformation="pct_change",
    )
    assert evidence
    assert evidence[0].method == "pearson"
    assert evidence[1].method == "spearman"
    assert evidence[0].sample_size >= 12


def test_risk_analytics_exposes_market_correlation_contract() -> None:
    rows = []
    for index in range(18):
        month = date(2023, 1, 31) + timedelta(days=30 * index)
        rows.append(
            {
                "loan_id": "L1",
                "snapshot_date": month.isoformat(),
                "outstanding_principal": 1000,
                "dpd": index + 30,
            }
        )
    market = _series("NQ=F", [100 + index * 2 for index in range(18)])
    result = RiskAnalyticsService().analyze(rows, market_series=market)
    assert "market_correlation" in result
    assert isinstance(result["market_correlation"], list)
    if result["market_correlation"]:
        finding = result["market_correlation"][0]
        assert finding["portfolio_metric"] in {"par30", "par60", "par90"}
        assert finding["market_metric"] == "NQ=F"
        assert "causality" not in finding["classification"].lower()
