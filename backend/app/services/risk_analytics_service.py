from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.analytics.npl import NPLAnalyticsService
from app.analytics.risk_analytics import RiskAnalyticsService
from app.data.persistence import PortfolioPersistenceService
from app.schemas.portfolio_schemas import PortfolioDashboardResponse


class RiskAnalyticsDashboardService:
    """Build the deterministic Portfolio Dashboard presentation contract."""

    def __init__(
        self,
        persistence: PortfolioPersistenceService | None = None,
        analytics: RiskAnalyticsService | None = None,
        npl: NPLAnalyticsService | None = None,
    ) -> None:
        self.persistence = persistence or PortfolioPersistenceService()
        self.analytics = analytics or RiskAnalyticsService()
        self.npl = npl or NPLAnalyticsService()

    def build_portfolio_dashboard(
        self,
        dataset_id: str,
        segment: str | None = None,
        cutoff_date: str | None = None,
    ) -> dict[str, Any]:
        rows = self.persistence.portfolio_records.find(
            {"dataset_id": dataset_id},
            limit=100_000,
        )
        if not rows:
            raise KeyError(dataset_id)

        available_segments = sorted({
            str(row.get("segment")).strip()
            for row in rows
            if row.get("segment") not in (None, "")
        })
        cutoff_dates = sorted({
            self._snapshot_key(row)
            for row in rows
            if self._snapshot_key(row)
        })

        filtered = self._filter_rows(rows, segment, cutoff_date)
        if not filtered:
            raise ValueError("No portfolio observations match the requested filters.")

        deterministic = self.analytics.analyze(filtered)
        current = self.analytics.latest_snapshot(filtered)
        active = [
            row for row in current
            if self._number(row.get("outstanding_principal")) > 0
        ]
        exposure = sum(self._number(row.get("outstanding_principal")) for row in active)
        par = deterministic.get("par", {})
        npl = self.npl.analyze(current)

        kpis = {
            "exposure": {"formatted": self._money(exposure), "subtext": "Outstanding balance"},
            "active_loans": {"formatted": self._integer(len(active)), "subtext": "Included in portfolio"},
            "par30": {"formatted": self._percent(par.get("par30", {}).get("ratio")), "subtext": self._money(par.get("par30", {}).get("balance"))},
            "par60": {"formatted": self._percent(par.get("par60", {}).get("ratio")), "subtext": self._money(par.get("par60", {}).get("balance"))},
            "par90": {"formatted": self._percent(par.get("par90", {}).get("ratio")), "subtext": self._money(par.get("par90", {}).get("balance"))},
            "npl": {"formatted": self._percent(npl.get("ratio")), "subtext": self._money(npl.get("balance"))},
        }

        rating_distribution = self._rating_distribution(active)
        heatmap = self._heatmap(deterministic.get("concentration", {}).get("segments", []))
        vintage = self._vintage(filtered)
        risk_drivers = self._risk_drivers(deterministic.get("drivers", []))

        structure = {
            "ratingDistribution": [
                {"label": item["rating"], "value": item["exposure"], "exposure": item["exposure"]}
                for item in rating_distribution
            ]
        }
        concentration = {
            "heatmap": [
                {
                    "id": f"{item['row']}:{item['column']}",
                    "label": item["label"],
                    "displayValue": item["formatted_exposure"],
                    "exposure": item["formatted_exposure"],
                    "intensity": item["risk_intensity"],
                    "par30": self._number(item["formatted_risk"].rstrip("%")) / 100,
                }
                for item in heatmap
            ]
        }
        vintage_view = self._vintage_view(vintage)

        response = PortfolioDashboardResponse(
            dataset_id=dataset_id,
            snapshot_date=self.analytics.snapshot_label(current),
            kpis=kpis,
            rating_distribution=rating_distribution,
            heatmap=heatmap,
            vintage=vintage,
            risk_drivers=risk_drivers,
            filters={"segments": available_segments, "cutoff_dates": cutoff_dates},
            structure=structure,
            concentration=concentration,
            vintage_view=vintage_view,
        )
        return response.model_dump()

    def _filter_rows(
        self,
        rows: list[dict[str, Any]],
        segment: str | None,
        cutoff_date: str | None,
    ) -> list[dict[str, Any]]:
        selected = rows
        if segment:
            wanted = segment.strip().casefold()
            selected = [
                row for row in selected
                if str(row.get("segment") or "").strip().casefold() == wanted
            ]
        if cutoff_date:
            cutoff = cutoff_date[:10]
            selected = [
                row for row in selected
                if not self._snapshot_key(row) or self._snapshot_key(row) <= cutoff
            ]
        return selected

    def _rating_distribution(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        groups: dict[str, float] = defaultdict(float)
        for row in rows:
            balance = self._number(row.get("outstanding_principal"))
            if balance <= 0:
                continue
            rating = (
                row.get("rating")
                or row.get("risk_rating")
                or row.get("rating_grade")
                or self._dpd_rating(self._number(row.get("dpd")))
            )
            groups[str(rating)] += balance
        return [
            {"rating": rating, "exposure": round(balance, 2)}
            for rating, balance in sorted(groups.items(), key=lambda item: item[1], reverse=True)
        ]

    def _heatmap(self, segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "row": str(item.get("key") or "unknown"),
                "column": "portfolio",
                "label": str(item.get("label") or item.get("key") or "Unknown"),
                "formatted_exposure": self._money(item.get("balance")),
                "formatted_risk": self._percent(item.get("par30")),
                "risk_intensity": item.get("par30", 0),
            }
            for item in segments
        ]

    def _vintage(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        current = self.analytics.latest_snapshot(rows)
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in current:
            value = row.get("origination_date")
            if value not in (None, ""):
                groups[str(value)[:7]].append(row)

        result = []
        for vintage, items in sorted(groups.items()):
            exposure = sum(self._number(row.get("outstanding_principal")) for row in items)
            par30_balance = sum(
                self._number(row.get("outstanding_principal"))
                for row in items
                if self._number(row.get("dpd")) >= 30
            )
            par30 = par30_balance / exposure if exposure else 0.0
            result.append({
                "vintage": vintage,
                "formatted_value": self._percent(par30),
                "formatted_exposure": self._money(exposure),
                "risk_intensity": par30,
            })
        return result

    def _risk_drivers(self, drivers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "id": str(driver.get("id") or f"driver:{index}"),
                "name": str(driver.get("title") or driver.get("label") or driver.get("id") or f"Driver {index + 1}"),
                "description": str(driver.get("evidence") or driver.get("description") or "Deterministic risk evidence."),
                "value": self._percent(driver.get("exposure_share")),
            }
            for index, driver in enumerate(drivers)
        ]

    def _vintage_view(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "rows": [
                {
                    "cohort": item["vintage"],
                    "risk": {"displayValue": item["formatted_value"], "value": item["risk_intensity"]},
                    "exposure": {"displayValue": item["formatted_exposure"], "value": item["formatted_exposure"]},
                }
                for item in items
            ],
            "columns": [
                {"key": "risk", "label": "PAR30"},
                {"key": "exposure", "label": "Exposure"},
            ],
        }

    @staticmethod
    def _dpd_rating(dpd: float) -> str:
        if dpd >= 90:
            return "90+ DPD"
        if dpd >= 60:
            return "60-89 DPD"
        if dpd >= 30:
            return "30-59 DPD"
        if dpd > 0:
            return "1-29 DPD"
        return "Current"

    @staticmethod
    def _snapshot_key(row: dict[str, Any]) -> str:
        for field in ("snapshot_date", "snapshot_month", "as_of_date"):
            value = row.get(field)
            if value not in (None, ""):
                return str(value)[:10]
        return ""

    @staticmethod
    def _number(value: Any) -> float:
        try:
            return max(float(value or 0), 0.0)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _money(cls, value: Any) -> str:
        return f"$ {cls._number(value):,.0f}"

    @classmethod
    def _percent(cls, value: Any) -> str:
        return f"{cls._number(value) * 100:.2f}%"

    @staticmethod
    def _integer(value: Any) -> str:
        return f"{int(value or 0):,}"
