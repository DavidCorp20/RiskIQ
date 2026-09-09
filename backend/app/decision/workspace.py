from __future__ import annotations

from typing import Any

from app.decision.decision_center import DecisionCenterService
from app.decision.decision_pipeline import DecisionPipelineService
from app.decision.rule_builder import RuleBuilder


class DecisionWorkspaceService:
    """Expose one deterministic orchestration contract for the RiskIQ UI."""

    CONTRACT_VERSION = "workspace-v1"

    def __init__(self) -> None:
        self.builder = RuleBuilder()
        self.pipeline = DecisionPipelineService()
        self.center = DecisionCenterService()

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        current = dict(payload.get("current") or {})
        previous = dict(payload.get("previous") or {})
        analysis = payload.get("current_analysis")
        history_entries = list(payload.get("history_entries") or [])
        raw_rules = list(payload.get("custom_rules") or [])

        compiled_rules: list[dict[str, Any]] = []
        rule_errors: list[dict[str, Any]] = []
        for index, raw_rule in enumerate(raw_rules):
            compiled = self.builder.compile(raw_rule)
            if compiled["valid"]:
                compiled_rules.append(compiled["compiled_rule"])
            else:
                rule_errors.append({"index": index, "errors": compiled["errors"]})

        if rule_errors:
            return {
                "status": "invalid_rules",
                "contract_version": self.CONTRACT_VERSION,
                "rule_errors": rule_errors,
                "workspace": None,
            }

        pipeline = self.pipeline.build(
            current=current,
            previous=previous,
            current_analysis=analysis,
            custom_rules=compiled_rules,
        )
        center = self.center.build(
            pipeline=pipeline,
            history_entries=history_entries,
        )

        return {
            "status": pipeline["status"],
            "contract_version": self.CONTRACT_VERSION,
            "rule_count": len(compiled_rules),
            "pipeline": pipeline,
            "decision_center": center,
            "governance": {
                "analytics_are_deterministic": True,
                "ai_interpretation_must_be_grounded": True,
                "customer_actions_executed": False,
            },
        }
