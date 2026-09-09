from __future__ import annotations

from app.analytics.npl import NPLAnalyticsService
from app.analytics.portfolio_intelligence import PortfolioIntelligenceService
from app.analytics.snapshot_engine import SnapshotEngine
from app.analytics.vintage_rollrate import VintageRollRateService
from app.data.normalizer import DataNormalizer, FieldMapping
from app.data.portfolio_projection import PortfolioProjectionService
from app.decision.workspace import DecisionWorkspaceService


def test_excel_like_rows_flow_from_mapping_to_decision_workspace() -> None:
    source_rows = [
        {
            "customer_code": "C001",
            "loan_number": "L001",
            "balance": 1000,
            "scheduled": 500,
            "paid": 0,
            "due": "2026-08-01",
            "segment_name": "retail",
            "days_late": 45,
            "originated": "2026-05-01",
            "state": "active",
        },
        {
            "customer_code": "C002",
            "loan_number": "L002",
            "balance": 2000,
            "scheduled": 1000,
            "paid": 900,
            "due": "2026-09-01",
            "segment_name": "retail",
            "days_late": 8,
            "originated": "2026-07-01",
            "state": "active",
        },
        {
            "customer_code": "C003",
            "loan_number": "L003",
            "balance": 1500,
            "scheduled": 750,
            "paid": 0,
            "due": "2026-05-01",
            "segment_name": "micro",
            "days_late": 100,
            "originated": "2026-02-01",
            "state": "active",
        },
    ]
    mappings = [
        FieldMapping(source="customer_code", target="customer_id", required=True),
        FieldMapping(source="loan_number", target="loan_id", required=True),
        FieldMapping(source="balance", target="outstanding_principal"),
        FieldMapping(source="scheduled", target="scheduled_amount"),
        FieldMapping(source="paid", target="paid_amount"),
        FieldMapping(source="due", target="due_date"),
        FieldMapping(source="segment_name", target="segment"),
        FieldMapping(source="days_late", target="dpd"),
        FieldMapping(source="originated", target="origination_date"),
        FieldMapping(source="state", target="status"),
    ]

    normalized = DataNormalizer().normalize(source_rows, mappings)
    assert DataNormalizer().validate_required(
        normalized, {"customer_id", "loan_id"}
    ) == []

    projection = PortfolioProjectionService().project(normalized)
    assert projection["summary"]["customer_count"] == 3
    assert projection["summary"]["loan_count"] == 3
    assert projection["summary"]["installment_count"] == 3

    snapshot = SnapshotEngine().build(
        projection["loans"], projection["installments"], "2026-09-09", "dataset-e2e"
    )
    assert snapshot["active_loans"] == 3
    assert float(snapshot["outstanding_balance"]) == 4500

    analysis = PortfolioIntelligenceService().analyze(normalized)
    assert analysis["portfolio"]["loans"] == 3
    assert analysis["portfolio"]["balance"] == 4500
    assert analysis["segments"]

    npl = NPLAnalyticsService().analyze(normalized)
    assert npl["available"] is True
    assert npl["regulatory_definition"] is False
    assert npl["affected_loans"] == 1

    vintage = VintageRollRateService().analyze(normalized)
    assert "vintages" in vintage
    assert vintage["roll_rate_available"] is False

    workspace = DecisionWorkspaceService().run(
        {
            "current": snapshot,
            "previous": snapshot,
            "current_analysis": analysis,
            "custom_rules": [],
        }
    )
    assert workspace["contract_version"] == "workspace-v1"
    assert workspace["governance"]["customer_actions_executed"] is False
    assert "decision_center" in workspace
    assert workspace["decision_center"]["counts"]["total_cards"] >= 1


def test_decision_workspace_rejects_invalid_custom_rule() -> None:
    workspace = DecisionWorkspaceService().run(
        {
            "current": {"outstanding_balance": 1000, "par30": 0.1, "par90": 0.0},
            "previous": {"outstanding_balance": 1000, "par30": 0.1, "par90": 0.0},
            "current_analysis": {"portfolio": {"loans": 1, "balance": 1000, "par30": 0.1, "par90": 0.0}, "segments": []},
            "custom_rules": [
                {
                    "id": "bad-rule",
                    "name": "Bad rule",
                    "mode": "unsupported",
                    "conditions": [],
                    "actions": [],
                }
            ],
        }
    )
    assert workspace["status"] == "invalid_rules"
    assert workspace["workspace"] is None
    assert workspace["rule_errors"]
