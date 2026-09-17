from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi.testclient import TestClient

from app.api.v1.endpoints import risk as risk_endpoint
from app.main import app
from app.repositories.risk_repository import RiskAnalysisRepository


class FakeCursor:
    def __init__(self, documents: list[dict[str, Any]]) -> None:
        self.documents = documents

    def sort(self, field: str, direction: int) -> "FakeCursor":
        reverse = direction < 0
        self.documents = sorted(
            self.documents,
            key=lambda document: document.get(field, datetime.min),
            reverse=reverse,
        )
        return self

    def limit(self, value: int) -> "FakeCursor":
        self.documents = self.documents[:value]
        return self

    def __iter__(self):
        return iter(self.documents)


class FakeCollection:
    def __init__(self) -> None:
        self.documents: list[dict[str, Any]] = []

    def insert_one(self, document: dict[str, Any]) -> None:
        self.documents.append(dict(document))

    def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        for document in self.documents:
            if all(document.get(key) == value for key, value in query.items()):
                return dict(document)
        return None

    def find(self, query: dict[str, Any]) -> FakeCursor:
        matches = [
            dict(document)
            for document in self.documents
            if all(document.get(key) == value for key, value in query.items())
        ]
        return FakeCursor(matches)


class FakeDatabase:
    def __init__(self, collection: FakeCollection) -> None:
        self.collection = collection

    def __getitem__(self, name: str) -> FakeCollection:
        assert name == "risk_analysis_results"
        return self.collection


class FakeMongoClient:
    def __init__(self) -> None:
        self.collection = FakeCollection()
        self.database = FakeDatabase(self.collection)

    def __getitem__(self, name: str) -> FakeDatabase:
        return self.database


def test_save_and_read_analysis_by_result_id() -> None:
    repository = RiskAnalysisRepository(
        client=FakeMongoClient(),
        database_name="test_riskiq",
    )
    payload = {
        "available": True,
        "exposure": 1500.0,
        "integrity": {
            "exposure_reconciled": True,
            "cumulative_par_monotonic": True,
            "non_negative": True,
        },
        "migration": {
            "t0": "2026-08-01",
            "t1": "2026-09-01",
        },
    }

    result_id = repository.save_analysis(
        dataset_id="dataset-1",
        payload=payload,
        engine_version="1.0.0",
    )
    stored = repository.get_analysis_by_id(result_id)

    assert result_id
    assert stored is not None
    assert stored["result_id"] == result_id
    assert stored["dataset_id"] == "dataset-1"
    assert stored["engine_version"] == "1.0.0"
    assert stored["t0_snapshot"] == "2026-08-01"
    assert stored["t1_snapshot"] == "2026-09-01"
    assert stored["integrity_status"] == "valid"
    assert stored["payload"] == payload
    assert stored["calculated_at"].endswith("+00:00")


def _api_rows() -> list[dict[str, Any]]:
    return [
        {
            "loan_id": "L1",
            "outstanding_principal": 1000,
            "dpd": 0,
            "segment": "retail",
            "snapshot_date": "2026-09-01",
        },
        {
            "loan_id": "L2",
            "outstanding_principal": 500,
            "dpd": 45,
            "segment": "retail",
            "snapshot_date": "2026-09-01",
        },
    ]


def test_api_persist_true_injects_result_id(monkeypatch) -> None:
    expected_result_id = "result-123"

    class FakeRepository:
        def __init__(self) -> None:
            pass

        def save_analysis(
            self,
            dataset_id: str,
            payload: dict[str, Any],
            engine_version: str = "1.0.0",
        ) -> str:
            assert dataset_id == "api-persist"
            assert payload["exposure"] == 1500
            return expected_result_id

    monkeypatch.setattr(risk_endpoint, "RiskAnalysisRepository", FakeRepository)
    client = TestClient(app)

    response = client.post(
        "/api/v1/risk/analytics?persist=true",
        json={"dataset_id": "api-persist", "rows": _api_rows()},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result_id"] == expected_result_id
    assert body["metadata"]["persistence"]["requested"] is True
    assert body["metadata"]["persistence"]["persisted"] is True


def test_api_mongo_failure_is_fail_open(monkeypatch) -> None:
    class FailingRepository:
        def __init__(self) -> None:
            raise RuntimeError("MongoDB unavailable")

    monkeypatch.setattr(risk_endpoint, "RiskAnalysisRepository", FailingRepository)
    client = TestClient(app)

    response = client.post(
        "/api/v1/risk/analytics?persist=true",
        json={"dataset_id": "api-failure", "rows": _api_rows()},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["exposure"] == 1500
    assert body["result_id"] is None
    assert body["metadata"]["persistence"]["requested"] is True
    assert body["metadata"]["persistence"]["persisted"] is False
    assert body["metadata"]["persistence"]["warning"]
    assert body["metadata"]["persistence"]["error_type"] == "RuntimeError"
