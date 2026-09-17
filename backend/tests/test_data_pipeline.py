from __future__ import annotations

from app.data.normalizer import DataNormalizer, FieldMapping


def test_normalized_rows_keep_source_columns_and_confirmed_canonical_fields() -> None:
    rows = [{"customer_code": "C001", "loan_number": "L001", "balance": 1250}]
    mappings = [
        FieldMapping(source="customer_code", target="customer_id", required=True),
        FieldMapping(source="loan_number", target="loan_id", required=True),
        FieldMapping(source="balance", target="outstanding_principal"),
    ]

    normalized = DataNormalizer().normalize(rows, mappings)

    assert normalized[0]["customer_id"] == "C001"
    assert normalized[0]["loan_id"] == "L001"
    assert normalized[0]["outstanding_principal"] == 1250
    assert normalized[0]["customer_code"] == "C001"
    assert normalized[0]["loan_number"] == "L001"
    assert normalized[0]["balance"] == 1250


def test_required_validation_detects_missing_customer() -> None:
    rows = [{"loan_id": "L001"}]
    errors = DataNormalizer().validate_required(rows, {"customer_id", "loan_id"})

    assert errors == ["row 0: missing customer_id"]
