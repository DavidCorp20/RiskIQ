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
        return {
            "status": status,
            "executive_summary": self._summary(status, critical, high, len(cards)),
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
            "trend": pipeline.get("history", {}),
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
    def _summary(status: str, critical: int, high: int, total: int) -> str:
        if critical:
            return f"La cartera requiere atención crítica: {critical} decisión(es) crítica(s) y {total} señal(es) en total."
        if high:
            return f"La cartera presenta señales relevantes: {high} decisión(es) de alta prioridad y {total} señal(es) en total."
        if status == "healthy":
            return "No se identificaron decisiones de alta prioridad con la evidencia disponible."
        return f"El motor mantiene {total} señal(es) para revisión humana."

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
