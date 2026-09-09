from app.data.portfolio_projection import PortfolioProjectionService


def test_projection_deduplicates_customers_and_loans() -> None:
    rows = [
        {
            "customer_id": "C1",
            "loan_id": "L1",
            "product_id": "P1",
            "origination_date": "2026-01-15",
            "outstanding_principal": "1000",
            "segment": "A",
            "due_date": "2026-02-15",
            "scheduled_amount": "100",
            "paid_amount": "50",
        },
        {
            "customer_id": "C1",
            "loan_id": "L1",
            "product_id": "P1",
            "origination_date": "2026-01-15",
            "outstanding_principal": "1000",
            "segment": "A",
            "due_date": "2026-03-15",
            "scheduled_amount": "100",
            "paid_amount": "100",
        },
    ]

    result = PortfolioProjectionService().project(rows)

    assert result["summary"] == {
        "customer_count": 1,
        "loan_count": 1,
        "installment_count": 2,
        "payment_count": 2,
    }
    assert result["loans"][0]["outstanding_principal"] == 1000
    assert result["customers"][0]["segment"] == "A"


def test_projection_handles_optional_dates() -> None:
    result = PortfolioProjectionService().project(
        [{"customer_id": "C1", "loan_id": "L1", "outstanding_principal": "250"}]
    )

    assert result["loans"][0]["origination_date"] is None
    assert result["summary"]["installment_count"] == 0
