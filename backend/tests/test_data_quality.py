from app.data.quality import DataQualityService


def test_quality_blocks_duplicate_loan_ids() -> None:
    rows = [
        {"customer_id": "C1", "loan_id": "L1", "outstanding_principal": 100},
        {"customer_id": "C2", "loan_id": "L1", "outstanding_principal": 200},
    ]

    result = DataQualityService().assess(rows)

    assert result["status"] == "blocked"
    assert any(issue["code"] == "DUPLICATE_LOAN_ID" for issue in result["issues"])


def test_quality_detects_invalid_numbers_and_dates() -> None:
    rows = [
        {
            "customer_id": "C1",
            "loan_id": "L1",
            "outstanding_principal": "not-a-number",
            "origination_date": "invalid-date",
        }
    ]

    result = DataQualityService().assess(rows)

    codes = {issue["code"] for issue in result["issues"]}
    assert "INVALID_NUMBER_OUTSTANDING_PRINCIPAL" in codes
    assert "INVALID_DATE_ORIGINATION_DATE" in codes


def test_quality_passes_clean_rows() -> None:
    rows = [
        {
            "customer_id": "C1",
            "loan_id": "L1",
            "outstanding_principal": 100,
            "scheduled_amount": 20,
            "paid_amount": 10,
            "origination_date": "2026-01-15",
        }
    ]

    result = DataQualityService().assess(rows)

    assert result["status"] == "passed"
    assert result["quality_score"] > 80
    assert result["issue_count"] == 0
