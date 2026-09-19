from app.analytics.portfolio_ews import PortfolioEWSService


ROWS = [
    {"loan_id": "A", "snapshot_date": "2026-09-01", "origination_date": "2026-01-15", "segment": "Micro", "dpd": 0, "outstanding_principal": 1000},
    {"loan_id": "B", "snapshot_date": "2026-09-01", "origination_date": "2026-01-20", "segment": "Micro", "dpd": 40, "outstanding_principal": 100},
    {"loan_id": "A", "snapshot_date": "2026-09-08", "origination_date": "2026-01-15", "segment": "Micro", "dpd": 30, "outstanding_principal": 900},
    {"loan_id": "B", "snapshot_date": "2026-09-08", "origination_date": "2026-01-20", "segment": "Micro", "dpd": 60, "outstanding_principal": 100},
    {"loan_id": "C", "snapshot_date": "2026-09-08", "origination_date": "2026-02-01", "segment": "SME", "dpd": 0, "outstanding_principal": 1000},
]


def test_portfolio_par_trend_is_balance_weighted():
    result = PortfolioEWSService().summarize(ROWS)
    trend = result["trends"]["par30"]

    # Previous: 100 / 1100 = 9.09%; latest: 1000 / 2000 = 50%.
    assert trend["ratio_delta"] == 0.4091
    assert trend["direction"] == "deteriorating"


def test_portfolio_trend_does_not_average_loan_deltas():
    result = PortfolioEWSService().summarize(ROWS)
    cohort = result["cohort_deterioration"]

    micro = next(item for item in cohort if item["cohort"] == "2026-01")
    # Weighted by prior exposure: A +30*1000 and B +20*100 -> 29.09,
    # not the simple mean of individual deltas (25).
    assert micro["dpd_velocity_weighted"] == 29.0909


def test_segment_roll_rate_uses_previous_balance_as_denominator():
    result = PortfolioEWSService().summarize(ROWS)
    transition = next(
        item for item in result["roll_rates_by_segment"]
        if item["segment"] == "Micro"
        and item["from_bucket"] == "current"
        and item["to_bucket"] == "early_30_59"
    )

    assert transition["transition_balance"] == 1000
    assert transition["roll_rate_by_balance"] == 1.0


def test_high_ews_exposure_respects_high_score_threshold():
    result = PortfolioEWSService().summarize(ROWS)
    micro = next(item for item in result["ews_exposure_by_segment"] if item["segment"] == "Micro")

    assert micro["exposure"] == 1000

    # Contract: high_ews_score defaults to 50. The current Micro loans score
    # below 50, so their exposure remains outside the high-EWS bucket.
    assert micro["high_ews_exposure"] == 0
    assert micro["high_ews_exposure_share"] == 0
    assert micro["high_ews_loans"] == 0
    assert result["predictive_probability"] is False
