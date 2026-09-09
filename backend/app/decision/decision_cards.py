from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DecisionCard:
    """Human-readable decision object backed by deterministic evidence."""

    id: str
    title: str
    category: str
    severity: str
    priority: str
    trigger: str
    evidence: dict[str, Any]
    recommendation: str
    rationale: str
    confidence: float
    causality: str = "associative"
    status: str = "proposed"
    mode: str = "suggested"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "severity": self.severity,
            "priority": self.priority,
            "trigger": self.trigger,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "causality": self.causality,
            "status": self.status,
            "mode": self.mode,
        }


class DecisionCardService:
    """Converts decision recommendations into UI-ready Decision Cards."""

    def build(self, recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cards: list[DecisionCard] = []
        for index, recommendation in enumerate(recommendations, start=1):
            priority = recommendation.get("priority", "watch")
            severity = "critical" if priority == "critical" else priority
            code = str(recommendation.get("code", f"DECISION_{index}"))
            evidence = recommendation.get("evidence", {})
            confidence = self._confidence(evidence)
            cards.append(DecisionCard(
                id=f"decision-{index}-{code.lower()}",
                title=str(recommendation.get("title", "Recomendación de riesgo")),
                category=self._category(code),
                severity=severity,
                priority=priority,
                trigger=self._trigger(code, evidence),
                evidence=evidence,
                recommendation=str(recommendation.get("title", "Revisar situación")),
                rationale=str(recommendation.get("rationale", "")),
                confidence=confidence,
                causality="associative" if code == "INVESTIGATE_TOP_DRIVER" else "not_inferred",
                status="proposed",
                mode=str(recommendation.get("mode", "suggested")),
            ).to_dict())
        return cards

    @staticmethod
    def _category(code: str) -> str:
        if "COLLECTION" in code:
            return "collections"
        if "ORIGINATION" in code:
            return "origination"
        if "DRIVER" in code:
            return "risk-driver"
        return "portfolio-risk"

    @staticmethod
    def _trigger(code: str, evidence: dict[str, Any]) -> str:
        def format_pct(value: Any) -> str:
            try:
                return f"{float(value):.2%}"
            except (TypeError, ValueError):
                return str(value) if value is not None else "—"

        if code == "PRIORITIZE_COLLECTIONS":
            return f"PAR90 = {format_pct(evidence.get('par90'))}"
        if code == "REVIEW_ORIGINATION_RISK":
            return f"PAR30 = {format_pct(evidence.get('par30'))}"
        return "Risk driver identificado por el motor analítico"

    @staticmethod
    def _confidence(evidence: dict[str, Any]) -> float:
        raw = evidence.get("confidence")
        if raw is not None:
            try:
                return max(0.0, min(1.0, float(raw)))
            except (TypeError, ValueError):
                pass
        return 0.75
