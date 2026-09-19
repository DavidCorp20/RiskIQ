from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.analytics.ews_engine import EWSEngine
from app.analytics.risk_analytics import RiskAnalyticsService


class PortfolioEWSService:
    """Deterministic portfolio-level EWS aggregation over loan observations."""

    def __init__(self, ews_engine: EWSEngine | None = None) -> None:
        self.ews_engine = ews_engine or EWSEngine()

    def summarize(self, rows: list[dict[str, Any]], *, high_score: float = 50.0) -> dict[str, Any]:
        if not rows:
            return {"available": False, "methodology": "portfolio-ews-v1", "predictive_probability": False, "reason": "No portfolio observations supplied."}

        normalized = self._normalize(rows)
        snapshots = self._snapshot_rows(normalized)
        dates = sorted(snapshots)
        latest_date = dates[-1]
        previous_date = dates[-2] if len(dates) >= 2 else None
        latest = self._portfolio_snapshot(snapshots[latest_date])
        previous = self._portfolio_snapshot(snapshots[previous_date]) if previous_date else None
        ews = self.ews_engine.calculate(normalized)
        high_ews = [item for item in ews if item["score"] >= high_score]
        high_ews_exposure = sum(self._ews_balance(item) for item in high_ews)
        exposure = latest["exposure"]

        return {
            "available": True,
            "methodology": "portfolio-ews-v1",
            "predictive_probability": False,
            "as_of": latest_date,
            "previous_as_of": previous_date,
            "portfolio": {
                **latest,
                "high_ews_loans": len(high_ews),
                "high_ews_exposure": round(high_ews_exposure, 2),
                "high_ews_exposure_share": round(high_ews_exposure / exposure, 4) if exposure else 0,
            },
            "trends": self._trend(latest, previous),
            "roll_rates_by_segment": self._segment_roll_rates(normalized),
            "ews_exposure_by_segment": self._ews_exposure_by_segment(ews, normalized, high_score),
            "cohort_deterioration": self._cohort_velocity(normalized),
            "top_alerts": high_ews[:25],
            "guardrails": {
                "deterministic": True,
                "weighted_ratios": True,
                "individual_deltas_averaged": False,
                "roll_rates_are_observed": True,
                "causality_inferred": False,
                "predictive_probability": False,
            },
        }

    @staticmethod
    def _normalize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = []
        for row in rows:
            item = dict(row)
            item["_loan_id"] = str(row.get("loan_id") or row.get("id") or "").strip()
            item["_snapshot"] = RiskAnalyticsService._snapshot_key(row)
            item["_segment"] = str(row.get("segment") or "Unknown").strip() or "Unknown"
            item["_cohort"] = str(row.get("origination_date") or "Unknown")[:7]
            item["_balance"] = max(PortfolioEWSService._number(row.get("outstanding_principal")), 0.0)
            item["_dpd"] = max(PortfolioEWSService._number(row.get("dpd")), 0.0)
            if item["_loan_id"] and item["_snapshot"]:
                result.append(item)
        if not result:
            raise ValueError("loan_id and snapshot_date are required for portfolio EWS aggregation")
        return result

    @staticmethod
    def _snapshot_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        for row in rows:
            grouped[row["_snapshot"]][row["_loan_id"]] = row
        return {date: list(loans.values()) for date, loans in grouped.items()}

    @classmethod
    def _portfolio_snapshot(cls, rows: list[dict[str, Any]]) -> dict[str, Any]:
        exposure = sum(row["_balance"] for row in rows)

        def bucket(threshold: float) -> dict[str, Any]:
            balance = sum(row["_balance"] for row in rows if row["_dpd"] >= threshold)
            return {
                "balance": round(balance, 2),
                "ratio": round(balance / exposure, 4) if exposure else 0,
                "loans": sum(1 for row in rows if row["_dpd"] >= threshold),
            }

        return {
            "loans": len(rows),
            "exposure": round(exposure, 2),
            "par30": bucket(30),
            "par60": bucket(60),
            "par90": bucket(90),
        }

    @staticmethod
    def _trend(latest: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
        if previous is None:
            return {"available": False, "reason": "At least two portfolio snapshots are required."}
        result = {}
        for metric in ("par30", "par60", "par90"):
            delta = latest[metric]["ratio"] - previous[metric]["ratio"]
            result[metric] = {
                "ratio_delta": round(delta, 4),
                "balance_delta": round(latest[metric]["balance"] - previous[metric]["balance"], 2),
                "direction": "deteriorating" if delta > 0 else "improving" if delta < 0 else "stable",
            }
        result["exposure_delta"] = round(latest["exposure"] - previous["exposure"], 2)
        return {"available": True, **result}

    @classmethod
    def _segment_roll_rates(cls, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        histories: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            histories[row["_loan_id"]].append(row)
        transitions: dict[str, dict[str, dict[str, float]]] = defaultdict(
            lambda: defaultdict(lambda: {"balance": 0.0, "observations": 0.0})
        )
        for history in histories.values():
            ordered = sorted(history, key=lambda row: row["_snapshot"])
            for previous, current in zip(ordered, ordered[1:]):
                key = f"{RiskAnalyticsService._bucket_name(previous['_dpd'])}_to_{RiskAnalyticsService._bucket_name(current['_dpd'])}"
                item = transitions[current["_segment"]][key]
                item["balance"] += previous["_balance"]
                item["observations"] += 1
        output = []
        for segment, items in transitions.items():
            denominators: dict[str, float] = defaultdict(float)
            for key, item in items.items():
                denominators[key.split("_to_", 1)[0]] += item["balance"]
            for key, item in items.items():
                source, target = key.split("_to_", 1)
                output.append({
                    "segment": segment,
                    "from_bucket": source,
                    "to_bucket": target,
                    "transition_balance": round(item["balance"], 2),
                    "observations": int(item["observations"]),
                    "roll_rate_by_balance": round(item["balance"] / denominators[source], 4) if denominators[source] else 0,
                })
        return sorted(output, key=lambda item: item["transition_balance"], reverse=True)

    @classmethod
    def _ews_exposure_by_segment(cls, ews: list[dict[str, Any]], rows: list[dict[str, Any]], high_score: float) -> list[dict[str, Any]]:
        latest_by_loan = {}
        for row in sorted(rows, key=lambda item: item["_snapshot"]):
            latest_by_loan[row["_loan_id"]] = row
        groups: dict[str, dict[str, float]] = defaultdict(lambda: {"exposure": 0.0, "high_ews_exposure": 0.0, "high_ews_loans": 0.0})
        for item in ews:
            row = latest_by_loan.get(item["loan_id"])
            if not row:
                continue
            segment = row["_segment"]
            balance = row["_balance"]
            groups[segment]["exposure"] += balance
            if item["score"] >= high_score:
                groups[segment]["high_ews_exposure"] += balance
                groups[segment]["high_ews_loans"] += 1
        return sorted([
            {
                "segment": segment,
                "exposure": round(v["exposure"], 2),
                "high_ews_exposure": round(v["high_ews_exposure"], 2),
                "high_ews_exposure_share": round(v["high_ews_exposure"] / v["exposure"], 4) if v["exposure"] else 0,
                "high_ews_loans": int(v["high_ews_loans"]),
            }
            for segment, v in groups.items()
        ], key=lambda item: item["high_ews_exposure"], reverse=True)

    @classmethod
    def _cohort_velocity(cls, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        snapshots = cls._snapshot_rows(rows)
        dates = sorted(snapshots)
        if len(dates) < 2:
            return []
        current = {r["_loan_id"]: r for r in snapshots[dates[-1]]}
        previous = {r["_loan_id"]: r for r in snapshots[dates[-2]]}
        cohorts: dict[str, dict[str, float]] = defaultdict(lambda: {"exposure": 0.0, "previous_exposure": 0.0, "dpd_weighted_delta": 0.0, "par30_current_balance": 0.0, "par30_previous_balance": 0.0})
        for loan_id, row in current.items():
            values = cohorts[row["_cohort"]]
            values["exposure"] += row["_balance"]
            if row["_dpd"] >= 30:
                values["par30_current_balance"] += row["_balance"]
            if loan_id in previous:
                prior = previous[loan_id]
                values["previous_exposure"] += prior["_balance"]
                values["dpd_weighted_delta"] += (row["_dpd"] - prior["_dpd"]) * prior["_balance"]
                if prior["_dpd"] >= 30:
                    values["par30_previous_balance"] += prior["_balance"]
        output = []
        for cohort, v in cohorts.items():
            output.append({
                "cohort": cohort,
                "exposure": round(v["exposure"], 2),
                "dpd_velocity_weighted": round(v["dpd_weighted_delta"] / v["previous_exposure"], 4) if v["previous_exposure"] else None,
                "par30_ratio_current": round(v["par30_current_balance"] / v["exposure"], 4) if v["exposure"] else 0,
                "par30_ratio_previous": round(v["par30_previous_balance"] / v["previous_exposure"], 4) if v["previous_exposure"] else None,
                "par30_ratio_delta": round(v["par30_current_balance"] / v["exposure"] - v["par30_previous_balance"] / v["previous_exposure"], 4) if v["exposure"] and v["previous_exposure"] else None,
            })
        return sorted(output, key=lambda item: item["exposure"], reverse=True)

    @staticmethod
    def _ews_balance(item: dict[str, Any]) -> float:
        features = item.get("features") or {}
        return float(features.get("current_balance") or 0)

    @staticmethod
    def _number(value: Any) -> float:
        try:
            return float(value) if value not in (None, "") else 0.0
        except (TypeError, ValueError):
            return 0.0
