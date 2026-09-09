from typing import Any

from app.api.schemas import DecisionRule


SUPPORTED_OPERATORS = {"eq", "neq", "gt", "gte", "lt", "lte", "in", "not_in"}


class DecisionEngine:
    """Deterministic, auditable rule evaluator.

    The engine evaluates declarative rules only. It never executes arbitrary
    customer code. The same contract can later be consumed by the visual
    builder, formula engine and AI rule generator.
    """

    def evaluate(self, facts: dict[str, Any], rules: list[DecisionRule]) -> dict[str, Any]:
        triggered_rules: list[str] = []
        actions: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []

        for rule in rules:
            if not rule.enabled:
                trace.append({"rule_id": rule.id, "status": "disabled"})
                continue

            condition_results = []
            for condition in rule.conditions:
                actual = facts.get(condition.field)
                matched = self._compare(actual, condition.operator, condition.value)
                condition_results.append(
                    {
                        "field": condition.field,
                        "operator": condition.operator,
                        "expected": condition.value,
                        "actual": actual,
                        "matched": matched,
                    }
                )

            matched = all(item["matched"] for item in condition_results)
            trace.append(
                {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "status": "triggered" if matched else "not_triggered",
                    "conditions": condition_results,
                    "mode": rule.mode,
                }
            )

            if matched:
                triggered_rules.append(rule.id)
                actions.extend(
                    [{"rule_id": rule.id, "mode": rule.mode, **action.model_dump()} for action in rule.actions]
                )

        return {
            "triggered_rules": triggered_rules,
            "actions": actions,
            "evaluation_trace": trace,
        }

    @staticmethod
    def _compare(actual: Any, operator: str, expected: Any) -> bool:
        if operator not in SUPPORTED_OPERATORS:
            raise ValueError(f"Unsupported operator: {operator}")

        if operator == "eq":
            return actual == expected
        if operator == "neq":
            return actual != expected
        if operator == "gt":
            return actual is not None and actual > expected
        if operator == "gte":
            return actual is not None and actual >= expected
        if operator == "lt":
            return actual is not None and actual < expected
        if operator == "lte":
            return actual is not None and actual <= expected
        if operator == "in":
            return actual in expected
        if operator == "not_in":
            return actual not in expected
        return False
