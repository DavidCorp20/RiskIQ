from __future__ import annotations

from collections import defaultdict
from typing import Any


class PortfolioIntelligenceService:
    """Produces deterministic portfolio views by segment and risk concentration."""

    def analyze(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            return {"portfolio": {}, "segments": [], "risk_drivers": [], "warnings": ["No hay datos para analizar."]}

        total_balance = sum(self._number(r.get("outstanding_principal")) for r in rows)
        total_loans = len(rows)
        overdue = [r for r in rows if self._number(r.get("dpd")) > 0]

        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            groups[str(row.get("segment") or "Sin segmento")].append(row)

        segments = []
        for name, items in sorted(groups.items(), key=lambda item: -sum(self._number(r.get("outstanding_principal")) for r in item[1])):
            balance = sum(self._number(r.get("outstanding_principal")) for r in items)
            dpd30_balance = sum(self._number(r.get("outstanding_principal")) for r in items if self._number(r.get("dpd")) >= 30)
            dpd90_balance = sum(self._number(r.get("outstanding_principal")) for r in items if self._number(r.get("dpd")) >= 90)
            par30 = dpd30_balance / balance if balance else 0
            par90 = dpd90_balance / balance if balance else 0
            segments.append({
                "segment": name,
                "loans": len(items),
                "balance": balance,
                "share_of_portfolio": round(balance / total_balance, 4) if total_balance else 0,
                "par30": round(par30, 4),
                "par90": round(par90, 4),
                "risk_level": "critical" if par90 >= 0.005 or par30 >= 0.08 else "high" if par30 >= 0.05 else "normal",
            })

        portfolio_par30 = sum(self._number(r.get("outstanding_principal")) for r in rows if self._number(r.get("dpd")) >= 30) / total_balance if total_balance else 0
        portfolio_par90 = sum(self._number(r.get("outstanding_principal")) for r in rows if self._number(r.get("dpd")) >= 90) / total_balance if total_balance else 0
        risk_drivers = self._drivers(segments, portfolio_par30)

        return {
            "portfolio": {
                "loans": total_loans,
                "balance": total_balance,
                "overdue_loans": len(overdue),
                "overdue_rate": round(len(overdue) / total_loans, 4),
                "par30": round(portfolio_par30, 4),
                "par90": round(portfolio_par90, 4),
            },
            "segments": segments,
            "risk_drivers": risk_drivers,
            "warnings": [],
        }

    @staticmethod
    def _drivers(segments: list[dict[str, Any]], portfolio_par30: float) -> list[dict[str, Any]]:
        drivers: list[dict[str, Any]] = []
        for segment in segments:
            if segment["par30"] > portfolio_par30 and segment["share_of_portfolio"] >= 0.10:
                drivers.append({
                    "type": "segment_deterioration",
                    "segment": segment["segment"],
                    "severity": segment["risk_level"],
                    "evidence": {
                        "segment_par30": segment["par30"],
                        "portfolio_par30": portfolio_par30,
                        "balance_share": segment["share_of_portfolio"],
                    },
                    "message": f"El segmento {segment['segment']} presenta PAR30 superior al promedio y representa una parte material de la exposición.",
                })
            if segment["share_of_portfolio"] >= 0.40:
                drivers.append({
                    "type": "concentration",
                    "segment": segment["segment"],
                    "severity": "warning",
                    "evidence": {"balance_share": segment["share_of_portfolio"]},
                    "message": f"El segmento {segment['segment']} concentra una proporción elevada de la cartera.",
                })
        return drivers

    @staticmethod
    def _number(value: Any) -> float:
        if value in (None, ""):
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
