from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.portfolio_routes as portfolio_routes
from app.services.risk_analytics_service import RiskAnalyticsDashboardService


class FakeRepository:
    def __init__(self, rows):
        self.rows = rows

    def find(self, filters=None, limit=100):
        filters = filters or {}
        return [row for row in self.rows if all(row.get(key) == value for key, value in filters.items())]


class FakePersistence:
    def __init__(self, rows):
        self.portfolio_records = FakeRepository(rows)


def test_dashboard_builds_contract_and_clamps_intensity():
    rows = [
        {"dataset_id": "d1", "loan_id": "L1", "snapshot_date": "2026-01-31", "segment": "Microcredito", "outstanding_principal": 1000, "dpd": 0, "origination_date": "2025-01-01"},
        {"dataset_id": "d1", "loan_id": "L2", "snapshot_date": "2026-01-31", "segment": "Microcredito", "outstanding_principal": 2000, "dpd": 45, "origination_date": "2025-01-01"},
        {"dataset_id": "d1", "loan_id": "L3", "snapshot_date": "2026-01-31", "segment": "Pyme", "outstanding_principal": 3000, "dpd": 95, "origination_date": "2024-06-01"},
    ]
    result = RiskAnalyticsDashboardService(persistence=FakePersistence(rows)).build_portfolio_dashboard("d1")
    assert result["contract_version"] == "portfolio-dashboard-v1"
    assert result["kpis"]["exposure"]["formatted"] == "$ 6,000"
    assert result["kpis"]["active_loans"]["formatted"] == "3"
    assert result["kpis"]["par30"]["formatted"] == "83.33%"
    assert result["kpis"]["par60"]["formatted"] == "50.00%"
    assert result["kpis"]["par90"]["formatted"] == "50.00%"
    assert result["kpis"]["npl"]["formatted"] == "50.00%"
    assert result["filters"]["segments"] == ["Microcredito", "Pyme"]
    assert all(0 <= item["risk_intensity"] <= 1 for item in result["heatmap"])
    assert all(0 <= item["risk_intensity"] <= 1 for item in result["vintage"])
    assert result["vintage_view"]["rows"]
    assert len(result["insights"]) == 4
    assert all(set(item) == {"type", "title", "message"} for item in result["insights"])


def test_dashboard_respects_segment_and_cutoff():
    rows = [
        {"dataset_id": "d1", "loan_id": "L1", "snapshot_date": "2026-01-31", "segment": "A", "outstanding_principal": 1000, "dpd": 0},
        {"dataset_id": "d1", "loan_id": "L1", "snapshot_date": "2026-02-28", "segment": "A", "outstanding_principal": 800, "dpd": 35},
        {"dataset_id": "d1", "loan_id": "L2", "snapshot_date": "2026-02-28", "segment": "B", "outstanding_principal": 2000, "dpd": 90},
    ]
    result = RiskAnalyticsDashboardService(persistence=FakePersistence(rows)).build_portfolio_dashboard("d1", segment="A", cutoff_date="2026-01-31")
    assert result["kpis"]["exposure"]["formatted"] == "$ 1,000"
    assert result["kpis"]["active_loans"]["formatted"] == "1"
    assert result["snapshot_date"] == "2026-01-31"


def test_dashboard_endpoint_exposes_exact_contract(monkeypatch):
    rows = [
        {"dataset_id": "d1", "loan_id": "L1", "snapshot_date": "2026-01-31", "segment": "A", "outstanding_principal": 1000, "dpd": 0, "origination_date": "2025-01-01"},
        {"dataset_id": "d1", "loan_id": "L2", "snapshot_date": "2026-01-31", "segment": "A", "outstanding_principal": 2000, "dpd": 45, "origination_date": "2025-01-01"},
    ]
    monkeypatch.setattr(portfolio_routes, "service", RiskAnalyticsDashboardService(persistence=FakePersistence(rows)))
    app = FastAPI()
    app.include_router(portfolio_routes.router)
    with TestClient(app) as client:
        response = client.get("/v1/portfolio/d1/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert {"contract_version", "dataset_id", "snapshot_date", "kpis", "rating_distribution", "heatmap", "vintage", "risk_drivers", "filters", "structure", "concentration", "vintage_view", "insights"} <= set(body)
    assert {"exposure", "active_loans", "par30", "par60", "par90", "npl"} <= set(body["kpis"])
    assert len(body["insights"]) == 4
    assert all(isinstance(item["message"], str) for item in body["insights"])
