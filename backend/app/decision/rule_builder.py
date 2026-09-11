from __future__ import annotations

from typing import Any


SUPPORTED_OPERATORS = {"eq", "neq", "gt", "gte", "lt", "lte", "in", "not_in", "between", "contains", "not_contains", "exists", "not_exists"}
SUPPORTED_ACTIONS = {"alert", "recommend", "set_risk_level", "review", "block"}
SUPPORTED_MODES = {"manual", "suggested", "approval", "automatic"}
SUPPORTED_LOGIC = {"AND", "OR"}


class RuleBuilder:
    """Validates and compiles rules created by the RiskIQ low-code UI."""

    def validate(self, rule: dict[str, Any]) -> dict[str, Any]:
        errors: list[str] = []
        if not rule.get("id"): errors.append("id is required")
        if not rule.get("name"): errors.append("name is required")
        if rule.get("logic", "AND") not in SUPPORTED_LOGIC: errors.append("unsupported logic")
        if rule.get("mode", "suggested") not in SUPPORTED_MODES: errors.append("unsupported mode")
        conditions = rule.get("conditions", [])
        if not conditions: errors.append("at least one condition is required")
        for index, condition in enumerate(conditions):
            if not condition.get("field"): errors.append(f"condition {index}: field is required")
            if condition.get("operator") not in SUPPORTED_OPERATORS: errors.append(f"condition {index}: unsupported operator")
            if "value" not in condition and condition.get("operator") not in {"exists", "not_exists"}: errors.append(f"condition {index}: value is required")
        actions = rule.get("actions", [])
        if not actions: errors.append("at least one action is required")
        for index, action in enumerate(actions):
            if action.get("type") not in SUPPORTED_ACTIONS: errors.append(f"action {index}: unsupported action")
        normalized = dict(rule)
        normalized.setdefault("logic", "AND")
        normalized.setdefault("mode", "suggested")
        normalized.setdefault("enabled", True)
        return {"valid": not errors, "errors": errors, "normalized_rule": normalized if not errors else None}

    def from_visual(self, payload: dict[str, Any]) -> dict[str, Any]:
        rule = {
            "id": payload.get("id", "visual-rule"),
            "name": payload.get("name", "Regla de riesgo"),
            "conditions": payload.get("conditions", []),
            "actions": payload.get("actions", []),
            "logic": payload.get("logic", "AND"),
            "mode": payload.get("mode", "suggested"),
            "enabled": payload.get("enabled", True),
        }
        return self.validate(rule)

    def compile(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.from_visual(payload)
        if not result["valid"]: return result
        rule = dict(result["normalized_rule"] or {})
        rule["builder_version"] = "2.0"
        rule["contract"] = "decision-engine-v2"
        return {"valid": True, "errors": [], "compiled_rule": rule}
