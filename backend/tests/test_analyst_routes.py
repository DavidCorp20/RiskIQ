from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.api.analyst_routes import DatasetService


class MockDatasetService:
    async def get_dataset_as_dataframe(self, dataset_id: str):
        import pandas as pd

        return pd.DataFrame(
            [
                {
                    "loan_id": "L001",
                    "customer_id": "C001",
                    "segment": "retail",
                    "outstanding_principal": 1000.0,
                    "dpd": 0,
                },
                {
                    "loan_id": "L002",
                    "customer_id": "C002",
                    "segment": "retail",
                    "outstanding_principal": 500.0,
                    "dpd": 35,
                },
            ]
        )


def test_analyst_query_returns_result(monkeypatch):
    monkeypatch.setattr(
        "app.api.analyst_routes.DatasetService",
        lambda: MockDatasetService(),
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/analyst/query",
        json={
            "dataset_id": "test-dataset",
            "dimensions": [{"field": "segment"}],
            "measures": [
                {"name": "exposure"},
                {"name": "loan_count"},
                {"name": "par30"},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["dataset_id"] == "test-dataset"
    assert body["dimensions"] == ["segment"]
    assert body["measures"] == ["exposure", "loan_count", "par30"]
    assert body["row_count"] == 1
    assert body["metadata"]["execution_engine"] == "pandas"


def test_analyst_query_returns_400_for_invalid_measure():
    client = TestClient(app)
    response = client.post(
        "/api/v1/analyst/query",
        json={
            "dataset_id": "test-dataset",
            "measures": [{"name": "unsupported_measure"}],
        },
    )

    assert response.status_code == 400
