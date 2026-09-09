from __future__ import annotations

from typing import Any


class DecisionLearningService:
    """Measures decision outcomes without pretending to infer causality."""

    def summarize(self, entries: list[dict[str, Any]]) -> dict[str, Any]:
        resolved = [item for item in entries if item.get("status") == "resolved"]
        outcomes = [item.get("outcome") or {} for item in resolved]
        improved = [item for item in outcomes if item.get("improved") is True]
        worsened = [item for item in outcomes if item.get("improved") is False]
        return {
            "total_decisions": len(entries),
            "resolved_decisions": len(resolved),
            "improved_count": len(improved),
            "worsened_count": len(worsened),
            "improvement_rate": len(improved) / len(resolved) if resolved else None,
            "methodology": "descriptive outcome tracking; no causal inference",
        }
