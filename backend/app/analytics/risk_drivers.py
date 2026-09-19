from __future__ import annotations

from typing import Any


class RiskDriverEngine:
    """Ranks observed risk drivers without claiming causal inference."""

    def build(self, analysis: dict[str, Any]) -> list[dict[str, Any]]:
        portfolio = analysis.get("portfolio", {})
        par30 = self._number(portfolio.get("par30"))
        drivers: list[dict[str, Any]] = []

        for segment in analysis.get("segments", []):
            segment_par30 = self._number(segment.get("par30"))
            share = self._number(segment.get("share_of_portfolio"))
            excess = max(segment_par30 - par30, 0)
            if excess <= 0 or share <= 0:
                continue
            score = excess * share
            drivers.append({
                "type": "segment",
                "key": segment.get("segment"),
                "impact_score": round(score, 6),
                "severity": "critical" if segment_par30 >= 0.08 else "high" if segment_par30 >= 0.05 else "watch",
                "evidence": {
                    "driver_par30": segment_par30,
                    "portfolio_par30": par30,
                    "excess_par30": round(excess, 4),
                    "exposure_share": share,
                    "exposure": segment.get("balance", 0),
                },
                "causality": "associative",
                "confidence": self._confidence(segment.get("loans", 0), share),
                "interpretation": "El segmento combina una mora superior al promedio con exposición material; es un driver observado, no una prueba causal.",
            })

        return sorted(drivers, key=lambda item: item["impact_score"], reverse=True)

    @staticmethod
    def _confidence(loans: Any, share: float) -> str:
        try:
            count = int(loans)
        except (TypeError, ValueError):
            count = 0
        if count >= 100 and share >= 0.20:
            return "high"
        if count >= 30 and share >= 0.10:
            return "medium"
        return "low"

    @staticmethod
    def _number(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
