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

        # Transparent sensitivity assumptions. Negative originations reduce exposure;
        # improved collections reduce delinquency. Approval cutoff has a conservative
        # directional effect only and is reported as an assumption, not a forecast.
        balance_factor = max(0.0, 1.0 + originations_change)
        estimated_balance = balance * balance_factor
        collection_factor = max(0.0, 1.0 - collection_change)
        estimated_par30 = min(1.0, max(0.0, par30 * collection_factor))
        estimated_par90 = min(1.0, max(0.0, par90 * collection_factor))

        if approval_change > 0:
            estimated_par30 *= max(0.0, 1.0 - min(0.20, approval_change / 1000.0))
            estimated_par90 *= max(0.0, 1.0 - min(0.20, approval_change / 1000.0))

        return {
            "name": name,
            "baseline": {"balance": balance, "par30": par30, "par90": par90},
            "scenario": {"balance": estimated_balance, "par30": estimated_par30, "par90": estimated_par90},
            "delta": {
                "balance": estimated_balance - balance,
                "par30": estimated_par30 - par30,
                "par90": estimated_par90 - par90,
            },
            "assumptions": {
                "originations_pct": originations_change,
                "collection_effectiveness_pct": collection_change,
                "approval_cutoff_points": approval_change,
            },
            "interpretation": "Sensibilidad histórica/transparente; no constituye una predicción ML.",
            "confidence": "medium",
        }

    @staticmethod
    def _number(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
