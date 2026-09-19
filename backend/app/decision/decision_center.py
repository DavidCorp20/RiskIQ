from __future__ import annotations

from typing import Any


class DecisionCenterService:
    """Build a deterministic, auditable decision view from pipeline evidence."""

    def build(self, pipeline: dict[str, Any], history_entries: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        cards = list(pipeline.get("cards", {}).get("items", []))
        drivers = list(pipeline.get("drivers", []))
        history = list(history_entries or [])
        trend = dict(pipeline.get("history", {}) or {})
        facts = dict(pipeline.get("facts", {}) or {})
        scorecard = dict(pipeline.get("scorecard", {}) or {})
        result = dict(pipeline.get("result", {}) or {})

        critical = sum(1 for card in cards if card.get("priority") == "critical")
        high = sum(1 for card in cards if card.get("priority") == "high")
        watch = sum(1 for card in cards if card.get("priority") not in {"critical", "high"})
        resolved = sum(1 for item in history if item.get("status") == "resolved")
        proposed = sum(1 for item in history if item.get("status") == "proposed")
        top_cards = sorted(cards, key=lambda x: self._priority_rank(x.get("priority")), reverse=True)
        top_drivers = sorted(drivers, key=lambda x: self._number(x.get("impact_score")), reverse=True)[:5]

        decision = result.get("decision") or result.get("outcome") or result.get("risk_level")
        triggered = list(result.get("triggered_rules") or [])
        reason_codes = list(result.get("reason_codes") or [])
        policy = {
            "id": result.get("policy_id") or pipeline.get("policy_id"),
            "version": result.get("policy_version") or pipeline.get("policy_version"),
            "name": result.get("policy_name") or pipeline.get("policy_name"),
        }

        return {
            "status": str(pipeline.get("status") or "healthy"),
            "executive_summary": self._summary(str(pipeline.get("status") or "healthy"), critical, high, len(cards), trend),
            "counts": {"critical": critical, "high": high, "watch": watch, "total_cards": len(cards), "proposed_history": proposed, "resolved_history": resolved},
            "priority_cards": top_cards[:10],
            "top_drivers": top_drivers,
            "decision_evidence": {
                "decision": decision,
                "customer_id": facts.get("customer_id"),
                "facts": facts,
                "scorecard": scorecard,
                "triggered_rules": triggered,
                "reason_codes": reason_codes,
                "formula_trace": list(result.get("formula_trace") or []),
                "evaluation_trace": list(result.get("evaluation_trace") or []),
                "policy": policy,
                "execution_mode": pipeline.get("execution_mode") or "test_only",
                "customer_actions_executed": bool(pipeline.get("customer_actions_executed", False)),
            },
            "decision_path": self._decision_path(pipeline, scorecard, triggered, decision),
            "trend": trend,
            "historical_change": {
                "available": bool(trend.get("previous_snapshot_date")),
                "status": str(trend.get("status") or "stable"),
                "summary": self._trend_summary(trend) if trend.get("previous_snapshot_date") else "No existe un snapshot previo comparable.",
                "drivers": list(trend.get("drivers") or [])[:5],
                "requires_human_review": True,
                "causality_inferred": False,
            },
            "next_actions": self._next_actions(top_cards),
            "governance": {"decision_mode": "human_review", "causality": "not_inferred", "evidence_required": True},
        }

    @staticmethod
    def _decision_path(pipeline: dict[str, Any], scorecard: dict[str, Any], triggered: list[Any], decision: Any) -> list[dict[str, Any]]:
        stages = list(pipeline.get("stages") or ["data", "normalize", "facts", "scorecard", "rules", "decision"])
        labels = {"data": "DATA", "normalize": "NORMALIZE", "facts": "FACTS", "formulas": "FORMULAS", "scorecard": "SCORE", "rules": "RULE", "risk_dsl": "RISK DSL", "decision": "DECISION"}
        output = []
        for stage in stages:
            item = {"stage": stage, "label": labels.get(stage, str(stage).upper()), "status": "complete", "evidence": None}
            if stage == "scorecard": item["evidence"] = scorecard.get("score")
            elif stage == "rules": item["evidence"] = triggered
            elif stage == "decision": item["evidence"] = decision
            output.append(item)
        return output

    @staticmethod
    def _priority_rank(priority: Any) -> int:
        return {"critical": 3, "high": 2, "watch": 1}.get(str(priority), 0)

    @staticmethod
    def _number(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _summary(status: str, critical: int, high: int, total: int, trend: dict[str, Any]) -> str:
        if critical:
            base = f"La cartera requiere atención crítica: {critical} decisión(es) crítica(s) y {total} señal(es) en total."
        elif high:
            base = f"La cartera presenta señales relevantes: {high} decisión(es) de alta prioridad y {total} señal(es) en total."
        elif status == "healthy":
            base = "No se identificaron decisiones de alta prioridad con la evidencia disponible."
        else:
            base = f"El motor mantiene {total} señal(es) para revisión humana."
        trend_summary = DecisionCenterService._trend_summary(trend) if trend.get("previous_snapshot_date") else ""
        return f"{base} {trend_summary}" if trend_summary else base

    @staticmethod
    def _trend_summary(trend: dict[str, Any]) -> str:
        status = str(trend.get("status") or "stable")
        changes = trend.get("changes") or {}
        parts: list[str] = []
        for metric in ("par30", "par90", "outstanding_balance"):
            change = changes.get(metric) or {}
            if change.get("delta") is None:
                continue
            if metric == "outstanding_balance":
                parts.append(f"exposición {float(change['delta']):+,.2f}")
            else:
                parts.append(f"{metric.upper()} {float(change['delta']):+.2%}")
        if not parts:
            return ""
        label = {"deteriorating": "Deterioro reciente", "improving": "Mejora reciente", "stable": "Evolución estable"}.get(status, "Evolución histórica")
        return f"{label}: " + " · ".join(parts) + "."

    @staticmethod
    def _next_actions(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"decision_id": card.get("id"), "action": "review", "label": "Revisar decisión", "priority": card.get("priority", "watch")} for card in cards[:5]]
