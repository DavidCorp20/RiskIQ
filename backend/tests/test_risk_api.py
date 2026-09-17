from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_post_analytics_single_snapshot_success() -> None:
    payload = {
        "dataset_id": "api-single-snapshot",
        "rows": [
            {
                "loan_id": "L1",
                "outstanding_principal": 100,
                "dpd": 0,
                "segment": "A",
                "origination_date": "2026-01-10",
                "snapshot_date": "2026-09-01",
                "product_id": "P1",
            },
            {
                "loan_id": "L2",
                "outstanding_principal": 200,
                "dpd": 35,
                "segment": "A",
                "origination_date": "2026-01-10",
                "snapshot_date": "2026-09-01",
                "product_id": "P1",
            },
        ],
    }

    response = client.post("/api/v1/risk/analytics", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["loan_count"] == 2
    assert body["exposure"] == 300
    assert set(body["dpd_buckets"]) == {
        "current",
        "dpd_1_29",
        "dpd_30_59",
        "dpd_60_89",
        "dpd_90_plus",
    }
    assert set(body["par"]) == {"par7", "par30", "par60", "par90"}
    assert body["par"]["par30"]["balance"] == 200
    assert body["par"]["par60"]["balance"] == 0
    assert body["par"]["par90"]["balance"] == 0


def test_post_analytics_multi_snapshot_includes_migration() -> None:
    payload = {
        "dataset_id": "api-multi-snapshot",
        "rows": [
            {
                "loan_id": "L1",
                "outstanding_principal": 100,
                "dpd": 0,
                "segment": "A",
                "origination_date": "2026-01-10",
                "snapshot_date": "2026-08-01",
                "product_id": "P1",
            },
            {
                "loan_id": "L2",
                "outstanding_principal": 200,
                "dpd": 10,
                "segment": "A",
                "origination_date": "2026-01-10",
                "snapshot_date": "2026-08-01",
                "product_id": "P1",
            },
            {
                "loan_id": "L1",
                "outstanding_principal": 100,
                "dpd": 35,
                "segment": "A",
                "origination_date": "2026-01-10",
                "snapshot_date": "2026-09-01",
                "product_id": "P1",
            },
            {
                "loan_id": "L2",
                "outstanding_principal": 200,
                "dpd": 0,
                "segment": "A",
                "origination_date": "2026-01-10",
                "snapshot_date": "2026-09-01",
                "product_id": "P1",
            },
        ],
    }

    response = client.post("/api/v1/risk/analytics", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert "migration" in body
    assert "deterioration_drivers" in body
    assert body["migration"]["available"] is True
    assert body["migration"]["t0"] == "2026-08-01"
    assert body["migration"]["t1"] == "2026-09-01"


def test_post_analytics_integrity_error_returns_422() -> None:
    payload = {
        "dataset_id": "api-integrity-error",
        "rows": [
            {
                "loan_id": "NEG-1",
                "outstanding_principal": -100,
                "dpd": 0,
                "segment": "A",
                "origination_date": "2026-01-10",
                "snapshot_date": "2026-09-01",
                "product_id": "P1",
            }
        ],
    }

    response = client.post("/api/v1/risk/analytics", json=payload)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "risk_integrity_error"
    assert "Negative outstanding_principal" in detail["message"]
    assert "2026-09-01" in detail["message"]
