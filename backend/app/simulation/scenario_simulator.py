from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Scenario:
    name: str
    changes: dict[str, float]


class ScenarioSimulator:
    """Applies transparent sensitivity assumptions to current portfolio metrics.

    This is not a predictive ML model. Results are directional scenario estimates.
    """

    def simulate(self, portfolio: dict[str, Any], changes: dict[str, float], name: str = "Custom scenario") -> dict[str, Any]:
        balance = self._number(portfolio.get("balance", portfolio.get("total_balance")))
        par30 = self._number(portfolio.get("par30"))
        par90 = self._number(portfolio.get("par90"))

        originations_change = self._number(changes.get("originations_pct"))
        collection_change = self._number(changes.get("collection_effectiveness_pct"))
        approval_change = self._number(changes.get("approval_cutoff_points"))

        balance_factor = max(0.0, 1.0 + originations_change)
        estimated_balance = balance * balance_factor
        collection_factor = max(0.0, 1.0 - collection_change)
        estimated_par30 = min(1.0, max(0.0, par30 * collection_factor))
        estimated_par90 = min(1.0, max(0.0, par90 * collection_factor))

        if approval_change > 0:
            cutoff_factor = max(0.0, 1.0 - min(0.20, approval_change / 1000.0))
            estimated_par30 *= cutoff_factor
            estimated_par90 *= cutoff_factor

        estimated_balance = self._round(estimated_balance)
        estimated_par30 = self._round(estimated_par30)
        estimated_par90 = self._round(estimated_par90)

        baseline_at_risk_30 = self._round(balance * par30)
        scenario_at_risk_30 = self._round(estimated_balance * estimated_par30)
        baseline_at_risk_90 = self._round(balance * par90)
        scenario_at_risk_90 = self._round(estimated_balance * estimated_par90)
        delta_at_risk_30 = self._round(scenario_at_risk_30 - baseline_at_risk_30)
        delta_at_risk_90 = self._round(scenario_at_risk_90 - baseline_at_risk_90)

        par30_delta = self._round(estimated_par30 - par30)
        par90_delta = self._round(estimated_par90 - par90)
        balance_delta = self._round(estimated_balance - balance)

        if par30_delta < 0 or par90_delta < 0:
            direction = "improves"
        elif par30_delta > 0 or par90_delta > 0:
            direction = "deteriorates"
        else:
            direction = "remains stable"

        return {
            "name": name,
            "baseline": {"balance": balance, "par30": par30, "par90": par90, "at_risk_30": baseline_at_risk_30, "at_risk_90": baseline_at_risk_90},
            "scenario": {"balance": estimated_balance, "par30": estimated_par30, "par90": estimated_par90, "at_risk_30": scenario_at_risk_30, "at_risk_90": scenario_at_risk_90},
            "delta": {"balance": balance_delta, "par30": par30_delta, "par90": par90_delta, "at_risk_30": delta_at_risk_30, "at_risk_90": delta_at_risk_90},
            "impact": {
                "par30_delta_pp": self._round(par30_delta * 100),
                "par90_delta_pp": self._round(par90_delta * 100),
                "at_risk_30_delta": delta_at_risk_30,
                "at_risk_90_delta": delta_at_risk_90,
                "direction": direction,
            },
            "assumptions": {
                "originations_pct": originations_change,
                "collection_effectiveness_pct": collection_change,
                "approval_cutoff_points": approval_change,
            },
            "interpretation": "Sensibilidad determinística sobre el snapshot actual; no constituye una predicción ML ni una estimación causal.",
            "governance": {
                "causality_inferred": False,
                "requires_human_review": True,
                "customer_actions_executed": False,
            },
            "confidence": "medium",
        }

    @staticmethod
    def _round(value: float) -> float:
        return round(value, 10)

    @staticmethod
    def _number(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
