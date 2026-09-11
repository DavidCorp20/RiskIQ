from typing import Any

from app.api.schemas import DecisionRule


SUPPORTED_OPERATORS = {"eq", "neq", "gt", "gte", "lt", "lte", "in", "not_in", "between", "contains", "not_contains", "exists", "not_exists"}
SUPPORTED_LOGIC = {"AND", "OR"}


class DecisionEngine:
    """Deterministic, auditable low-code rule evaluator.

    Rules are declarative JSON contracts. Customer code is never executed.
    The evaluator returns an explicit trace so every decision can be explained.
    """

    def evaluate(self, facts: dict[str, Any], rules: list[DecisionRule]) -> dict[str, Any]:
        triggered_rules: list[str] = []
        actions: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []

        for rule in rules:
            if not rule.enabled:
                trace.append({"rule_id": rule.id, "rule_name": rule.name, "status": "disabled"})
                continue

            results = []
            for condition in rule.conditions:
                actual = facts.get(condition.field)
                matched = self._compare(actual, condition.operator, condition.value)
                results.append({"field": condition.field, "operator": condition.operator, "expected": condition.value, "actual": actual, "matched": matched})

            logic = getattr(rule, "logic", "AND") or "AND"
            if logic not in SUPPORTED_LOGIC:
                raise ValueError(f"Unsupported condition logic: {logic}")
            matched = (all(x["matched"] for x in results) if logic == "AND" else any(x["matched"] for x in results))
            trace.append({"rule_id": rule.id, "rule_name": rule.name, "status": "triggered" if matched else "not_triggered", "conditions": results, "logic": logic, "mode": rule.mode})

            if matched:
                triggered_rules.append(rule.id)
                actions.extend([{"rule_id": rule.id, "mode": rule.mode, **action.model_dump()} for action in rule.actions])

        return {"triggered_rules": triggered_rules, "actions": actions, "evaluation_trace": trace}

    @staticmethod
    def _compare(actual: Any, operator: str, expected: Any) -> bool:
        if operator not in SUPPORTED_OPERATORS:
            raise ValueError(f"Unsupported operator: {operator}")
        if operator == "exists": return actual is not None
        if operator == "not_exists": return actual is None
        if actual is None: return False if operator not in {"neq", "not_in"} else True
        if operator == "eq": return actual == expected
        if operator == "neq": return actual != expected
        if operator == "gt": return actual > expected
        if operator == "gte": return actual >= expected
        if operator == "lt": return actual < expected
        if operator == "lte": return actual <= expected
        if operator == "in": return actual in expected
        if operator == "not_in": return actual not in expected
        if operator == "between": return isinstance(expected, (list, tuple)) and len(expected) == 2 and expected[0] <= actual <= expected[1]
        if operator == "contains": return expected in actual
        if operator == "not_contains": return expected not in actual
        return False
