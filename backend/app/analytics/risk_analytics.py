from __future__ import annotations

from collections import defaultdict
from typing import Any


class RiskAnalyticsService:
    """Deterministic point-in-time and longitudinal portfolio risk analytics."""

    BUCKETS = (
        ("current", 0, 1),
        ("early_1_29", 1, 30),
        ("early_30_59", 30, 60),
        ("late_60_89", 60, 90),
        ("hard_90_plus", 90, None),
    )

    def analyze(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        current = self.latest_snapshot(rows)
        active = [r for r in current if self._number(r.get("outstanding_principal")) > 0]
        exposure = sum(self._number(r.get("outstanding_principal")) for r in active)
        buckets = {
            "par7": self._bucket(active, 7, exposure),
            "par30": self._bucket(active, 30, exposure),
            "par60": self._bucket(active, 60, exposure),
            "par90": self._bucket(active, 90, exposure),
        }
        segments = self._concentration(active, exposure, "segment")
        products = self._concentration(active, exposure, "product_id")
        vintages = self._concentration(active, exposure, "origination_date", vintage=True)
        drivers: list[dict[str, Any]] = []
        for item in segments[:5]:
            if item["par30"] > 0:
                drivers.append({
                    "id": f"segment:{item['key']}",
                    "title": item.get("label", f"Segmento {item['key']}"),
                    "severity": "high" if item["par30"] >= 0.08 else "medium",
                    "evidence": f"{item['loans']} créditos, {item['share_of_exposure'] * 100:.1f}% de exposición y PAR30 de {item['par30'] * 100:.1f}%.",
                    "exposure_share": item["share_of_exposure"],
                    "confidence": "deterministic",
                })

        cro_evidence = self._cro_evidence(rows, active, exposure, buckets)

        return {
            "available": bool(active),
            "loan_count": len(active),
            "exposure": round(exposure, 2),
            "par": buckets,
            "concentration": {"segments": segments, "products": products},
            "vintage": vintages,
            "drivers": drivers,
            "cro_evidence": cro_evidence,
            "methodology": {
                "deterministic": True,
                "causality_inferred": False,
                "npl_regulatory_definition": False,
                "point_in_time": True,
                "longitudinal_migration": cro_evidence["migration"]["available"],
                "note": "Point-in-time PAR ratios use the latest available observation per loan. Longitudinal migration uses ordered snapshots per loan.",
            },
            "snapshot": self.snapshot_label(current),
        }

    @classmethod
    def latest_snapshot(cls, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []
        dated = [r for r in rows if cls._snapshot_key(r)]
        if not dated:
            return cls._dedupe_by_loan(rows)
        latest_date = max(cls._snapshot_key(r) for r in dated)
        return cls._dedupe_by_loan([r for r in rows if cls._snapshot_key(r) == latest_date])

    @classmethod
    def _dedupe_by_loan(cls, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        anonymous: list[dict[str, Any]] = []
        for row in rows:
            loan_id = str(row.get("loan_id") or row.get("id") or "").strip()
            if loan_id:
                latest[loan_id] = row
            else:
                anonymous.append(row)
        return list(latest.values()) + anonymous

    @staticmethod
    def _snapshot_key(row: dict[str, Any]) -> str:
        for field in ("snapshot_date", "snapshot_month", "as_of_date"):
            value = row.get(field)
            if value not in (None, ""):
                return str(value)[:10]
        return ""

    @classmethod
    def snapshot_label(cls, rows: list[dict[str, Any]]) -> str | None:
        keys = [cls._snapshot_key(r) for r in rows if cls._snapshot_key(r)]
        return max(keys) if keys else None

    def _bucket(self, rows: list[dict[str, Any]], dpd: int, total: float) -> dict[str, Any]:
        balance = sum(
            self._number(r.get("outstanding_principal"))
            for r in rows
            if self._number(r.get("dpd")) >= dpd
        )
        count = sum(1 for r in rows if self._number(r.get("dpd")) >= dpd)
        return {
            "balance": round(balance, 2),
            "ratio": round(balance / total, 4) if total else 0,
            "loans": count,
            "dpd_threshold": dpd,
        }

    def _cro_evidence(
        self,
        rows: list[dict[str, Any]],
        active: list[dict[str, Any]],
        exposure: float,
        buckets: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        par30 = buckets["par30"]["ratio"]
        par60 = buckets["par60"]["ratio"]
        par90 = buckets["par90"]["ratio"]
        par30_balance = buckets["par30"]["balance"]
        par60_balance = buckets["par60"]["balance"]
        par90_balance = buckets["par90"]["balance"]

        # The scenario is deliberately deterministic: it quantifies the maximum
        # balance currently in 30+ that could become 90+; it is not a forecast.
        early_30_89_balance = sum(
            self._number(r.get("outstanding_principal"))
            for r in active
            if 30 <= self._number(r.get("dpd")) < 90
        )
        early_30_59_balance = sum(
            self._number(r.get("outstanding_principal"))
            for r in active
            if 30 <= self._number(r.get("dpd")) < 60
        )
        late_60_89_balance = sum(
            self._number(r.get("outstanding_principal"))
            for r in active
            if 60 <= self._number(r.get("dpd")) < 90
        )
        migration = self._migration_evidence(rows)

        return {
            "version": "cro-evidence-v1",
            "as_of": self.snapshot_label(active),
            "exposure": {
                "total_balance": round(exposure, 2),
                "unit": "currency",
                "active_loans": len(active),
            },
            "par": {
                "par30": {"ratio": par30, "balance": round(par30_balance, 2), "impact_formula": "PAR30 × total_balance"},
                "par60": {"ratio": par60, "balance": round(par60_balance, 2), "impact_formula": "PAR60 × total_balance"},
                "par90": {"ratio": par90, "balance": round(par90_balance, 2), "impact_formula": "PAR90 × total_balance"},
            },
            "exposure_impact": {
                "par30_balance": round(par30 * exposure, 2),
                "par60_balance": round(par60 * exposure, 2),
                "par90_balance": round(par90 * exposure, 2),
                "early_30_59_balance": round(early_30_59_balance, 2),
                "late_60_89_balance": round(late_60_89_balance, 2),
                "30_to_89_balance_at_risk": round(early_30_89_balance, 2),
                "containment_gap_balance": round(max(par30_balance - par90_balance, 0.0), 2),
                "stress_if_30_to_89_migrates_to_90_plus": round(early_30_89_balance, 2),
                "stress_par90_ratio_if_30_to_89_migrates": round(
                    (par90_balance + early_30_89_balance) / exposure, 4
                ) if exposure else 0,
                "scenario_type": "deterministic_full_migration_stress",
                "forecast": False,
            },
            "migration": migration,
            "data_sufficiency": {
                "point_in_time_par": bool(active and exposure > 0),
                "longitudinal_migration": migration["available"],
                "segment": bool(active and any(str(r.get("segment") or "").strip() for r in active)),
                "vintage": bool(active and any(r.get("origination_date") for r in active)),
            },
        }

    def _migration_evidence(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        histories: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            loan_id = str(row.get("loan_id") or row.get("id") or "").strip()
            snapshot = self._snapshot_key(row)
            if loan_id and snapshot:
                histories[loan_id].append(row)

        transitions: dict[str, dict[str, float]] = defaultdict(lambda: {"balance": 0.0, "count": 0.0})
        ordered_snapshots = 0
        for loan_rows in histories.values():
            ordered = sorted(loan_rows, key=self._snapshot_key)
            if len(ordered) < 2:
                continue
            ordered_snapshots += len(ordered) - 1
            for previous, current in zip(ordered, ordered[1:]):
                source = self._bucket_name(self._number(previous.get("dpd")))
                target = self._bucket_name(self._number(current.get("dpd")))
                balance = self._number(previous.get("outstanding_principal"))
                key = f"{source}_to_{target}"
                transitions[key]["balance"] += balance
                transitions[key]["count"] += 1

        roll_rates = []
        for key, value in transitions.items():
            source, target = key.split("_to_", 1)
            denominator = sum(
                item["balance"]
                for transition, item in transitions.items()
                if transition.startswith(f"{source}_to_")
            )
            roll_rates.append({
                "from_bucket": source,
                "to_bucket": target,
                "transition_balance": round(value["balance"], 2),
                "observations": int(value["count"]),
                "roll_rate_by_balance": round(value["balance"] / denominator, 4) if denominator else 0,
            })

        early_to_hard = [
            item for item in roll_rates
            if item["from_bucket"] in {"early_30_59", "late_60_89"}
            and item["to_bucket"] == "hard_90_plus"
        ]
        early_balance = sum(
            item["transition_balance"]
            for item in roll_rates
            if item["from_bucket"] in {"early_30_59", "late_60_89"}
        )
        hard_migration_balance = sum(item["transition_balance"] for item in early_to_hard)

        return {
            "available": ordered_snapshots > 0,
            "transition_observations": ordered_snapshots,
            "roll_rates": sorted(roll_rates, key=lambda item: item["transition_balance"], reverse=True),
            "early_to_hard": {
                "transition_balance": round(hard_migration_balance, 2),
                "source_balance_observed": round(early_balance, 2),
                "roll_rate_by_balance": round(hard_migration_balance / early_balance, 4) if early_balance else 0,
            },
            "interpretation_guardrail": "Roll Rate is observed transition evidence, not a forecast of future default.",
        }

    @classmethod
    def _bucket_name(cls, dpd: float) -> str:
        for name, lower, upper in cls.BUCKETS:
            if dpd >= lower and (upper is None or dpd < upper):
                return name
        return "hard_90_plus"

    def _concentration(self, rows: list[dict[str, Any]], total: float, field: str, vintage: bool = False) -> list[dict[str, Any]]:
        groups: dict[str, dict[str, float]] = defaultdict(lambda: {"balance": 0.0, "loans": 0.0, "par30_balance": 0.0})
        labels: dict[str, str] = {}
        for row in rows:
            key, label = self._group_value(row, field, vintage)
            balance = self._number(row.get("outstanding_principal"))
            groups[key]["balance"] += balance
            groups[key]["loans"] += 1
            if self._number(row.get("dpd")) >= 30:
                groups[key]["par30_balance"] += balance
            labels[key] = label
        result = []
        for key, value in groups.items():
            result.append({
                "key": key,
                "label": labels.get(key, key),
                "loans": int(value["loans"]),
                "balance": round(value["balance"], 2),
                "share_of_exposure": round(value["balance"] / total, 4) if total else 0,
                "par30": round(value["par30_balance"] / value["balance"], 4) if value["balance"] else 0,
            })
        return sorted(result, key=lambda x: x["balance"], reverse=True)

    @staticmethod
    def _group_value(row: dict[str, Any], field: str, vintage: bool = False) -> tuple[str, str]:
        if vintage:
            key = str(row.get(field) or "Unknown")[:7]
            return key, key
        if field == "segment":
            explicit = str(row.get("segment") or "").strip()
            if explicit:
                return explicit, f"Segmento {explicit}"
            product = str(row.get("product_id") or row.get("product") or "").strip()
            if product:
                return f"product:{product}", f"Producto {product}"
            return "Unknown", "Sin segmentación"
        key = str(row.get(field) or "Unknown").strip() or "Unknown"
        return key, key

    @staticmethod
    def _number(value: Any) -> float:
        try:
            return max(float(value or 0), 0.0)
        except (TypeError, ValueError):
            return 0.0
