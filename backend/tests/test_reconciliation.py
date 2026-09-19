from app.data.reconciliation import classify, merge_enriched, preview


def base():
    return {
        "loan_id": "CR-1",
        "snapshot_date": "2025-01-01",
        "outstanding_principal": 1000,
        "dpd": 5,
        "status": "active",
        "paid_amount": 100,
        "scheduled_amount": 200,
        "region": None,
    }


def test_identical_observation_is_ignored():
    item = classify(base(), dict(base()))
    assert item.classification == "identical"
    assert item.added_fields == []
    assert item.conflicts == []


def test_missing_metadata_is_enriched_without_changing_financials():
    incoming = {**base(), "region": "North", "income": 2500}
    item = classify(base(), incoming)
    assert item.classification == "enriched"
    assert set(item.added_fields) == {"region", "income"}
    merged = merge_enriched(base(), incoming)
    assert merged["region"] == "North"
    assert merged["income"] == 2500
    assert merged["outstanding_principal"] == 1000


def test_critical_financial_change_is_conflict():
    incoming = {**base(), "dpd": 35, "status": "delinquent"}
    item = classify(base(), incoming)
    assert item.classification == "conflict"
    assert {x["field"] for x in item.conflicts} == {"dpd", "status"}
    assert all(x["critical"] for x in item.conflicts)


def test_new_observation_is_inserted():
    incoming = {**base(), "loan_id": "CR-2"}
    report = preview([], [incoming])
    assert report["counts"] == {"inserted": 1, "identical": 0, "enriched": 0, "conflict": 0}


def test_duplicate_identity_inside_file_is_not_inserted_twice():
    row = base()
    report = preview([], [row, dict(row)])
    assert report["counts"]["inserted"] == 1
    assert len(report["duplicate_in_file"]) == 1
