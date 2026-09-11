from __future__ import annotations

from typing import Any


class DecisionCenterService:
    """Build a deterministic executive view from pipeline and decision history."""

    def build(
        self,
        pipeline: dict[str, Any],
        history_entries: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        cards = list(pipeline.get("cards", {}).get("items", []))
        drivers = list(pipeline.get("drivers", []))
        history = list(history_entries or [])
        trend = dict(pipeline.get("history", {}) or {})

        critical = sum(1 for card in cards if card.get("priority") == "critical")
        high = sum(1 for card in cards if card.get("priority") == "high")
        watch = sum(1 for card in cards if card.get("priority") not in {"critical", "high"})
        resolved = sum(1 for item in history if item.get("status") == "resolved")
        proposed = sum(1 for item in history if item.get("status") == "proposed")

        top_cards = sorted(
            cards,
            key=lambda item: self._priority_rank(item.get("priority")),
            reverse=True,
        )
        top_drivers = sorted(
            drivers,
            key=lambda item: self._number(item.get("impact_score")),
            reverse=True,
        )[:5]

        status = str(pipeline.get("status") or "healthy")
        trend_status = str(trend.get("status") or "stable")
        trend_drivers = list(trend.get("drivers") or [])

        return {
            "status": status,
            "executive_summary": self._summary(status, critical, high, len(cards), trend),
            "counts": {
                "critical": critical,
                "high": high,
                "watch": watch,
                "total_cards": len(cards),
                "proposed_history": proposed,
                "resolved_history": resolved,
            },
            "priority_cards": top_cards[:10],
            "top_drivers": top_drivers,
            "trend": trend,
            "historical_change": {
                "available": bool(trend.get("trend_available")),
                "status": trend_status,
                "summary": self._trend_summary(trend),
                "drivers": trend_drivers[:5],
                "requires_human_review": True,
                "causality_inferred": False,
            },
            "next_actions": self._next_actions(top_cards),
            "governance": {
                "decision_mode": "human_review",
                "causality": "not_inferred",
                "evidence_required": True,
            },
        }

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
        base = ""
        if critical:
            base = f"La cartera requiere atención crítica: {critical} decisión(es) crítica(s) y {total} señal(es) en total."
        elif high:
            base = f"La cartera presenta señales relevantes: {high} decisión(es) de alta prioridad y {total} señal(es) en total."
        elif status == "healthy":
            base = "No se identificaron decisiones de alta prioridad con la evidencia disponible."
        else:
            base = f"El motor mantiene {total} señal(es) para revisión humana."
        trend_summary = DecisionCenterService._trend_summary(trend)
        return f"{base} {trend_summary}" if trend_summary else base

    @staticmethod
    def _trend_summary(trend: dict[str, Any]) -> str:
        if not trend or not trend.get("trend_available"):
            return ""
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
        actions: list[dict[str, Any]] = []
        for card in cards[:5]:
            actions.append({
                "decision_id": card.get("id"),
                "action": "review",
                "label": "Revisar decisión",
                "priority": card.get("priority", "watch"),
            })
        return actions
