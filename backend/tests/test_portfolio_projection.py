from app.data.portfolio_projection import PortfolioProjectionService


def test_projection_deduplicates_customers_and_loans_at_latest_observation() -> None:
    rows = [
        {
            "customer_id": "C1", "loan_id": "L1", "product_id": "P1", "origination_date": "2026-01-15",
            "snapshot_date": "2026-02-28", "outstanding_principal": "1000", "segment": "A",
            "due_date": "2026-02-15", "scheduled_amount": "100", "paid_amount": "50", "payment_date": "2026-02-16",
        },
        {
            "customer_id": "C1", "loan_id": "L1", "product_id": "P1", "origination_date": "2026-01-15",
            "snapshot_date": "2026-03-31", "outstanding_principal": "900", "segment": "A",
            "due_date": "2026-03-15", "scheduled_amount": "100", "paid_amount": "100", "payment_date": "2026-03-15",
        },
    ]

    result = PortfolioProjectionService().project(rows)

    assert result["summary"] == {
        "customer_count": 1,
        "loan_count": 1,
        "installment_count": 1,
        "payment_count": 1,
        "snapshot_date": "2026-03-31",
    }
    assert result["loans"][0]["outstanding_principal"] == 900
    assert result["customers"][0]["segment"] == "A"


def test_projection_handles_optional_dates() -> None:
    result = PortfolioProjectionService().project(
        [{"customer_id": "C1", "loan_id": "L1", "outstanding_principal": "250"}]
    )

    assert result["loans"][0]["origination_date"] is None
    assert result["summary"]["installment_count"] == 0
