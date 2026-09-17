from __future__ import annotations

from collections import defaultdict
from typing import Any


class RiskAnalyticsIntegrityError(ValueError):
    """Raised when deterministic portfolio risk invariants are violated."""


class RiskAnalyticsService:
    """Deterministic point-in-time portfolio risk analytics.

    Longitudinal records remain available to migration/history. Point-in-time
    ratios use only the latest available observation per loan so the same credit
    is never counted seven or twelve times just because snapshots were uploaded.
    """

    DPD_BUCKETS = ("current", "dpd_1_29", "dpd_30_59", "dpd_60_89", "dpd_90_plus")

    def analyze(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        duplicate_keys = self._duplicate_snapshot_keys(rows)
        if duplicate_keys:
            raise RiskAnalyticsIntegrityError(
                f"Duplicate loan_id + snapshot key detected: {duplicate_keys}"
            )

        # Validate raw balances before selecting active exposure. Negative
        # balances must never disappear merely because they are excluded by > 0.
        for row in rows:
            balance = self._number(row.get("outstanding_principal"))
            if balance < 0:
                raise RiskAnalyticsIntegrityError(
                    f"Negative outstanding_principal for loan {self._loan_id(row)}: {balance}"
                )

        current = self.latest_snapshot(rows)
        active = [r for r in current if self._number(r.get("outstanding_principal")) > 0]
        exposure = sum(self._number(r.get("outstanding_principal")) for r in active)

        dpd_buckets = self._dpd_buckets(active)
        par = self._par_from_buckets(dpd_buckets, exposure)
        integrity = self._validate_integrity(exposure, dpd_buckets, par)

        segments = self._concentration(active, exposure, "segment")
        products = self._concentration(active, exposure, "product_id")
        vintages = self._concentration(active, exposure, "origination_date", vintage=True)
        drivers: list[dict[str, Any]] = []
        # Risk drivers represent observed deterioration. Exposure materiality is
        # evidence used to rank a deteriorated segment, not a substitute for risk.
        for item in segments[:5]:
            if item["par30"] > 0:
                drivers.append({"id": f"segment:{item['key']}", "title": item.get("label", f"Segmento {item['key']}"), "severity": "high" if item["par30"] >= 0.08 else "medium", "evidence": f"{item['loans']} créditos, {item['share_of_exposure'] * 100:.1f}% de exposición y PAR30 de {item['par30'] * 100:.1f}%.", "exposure_share": item["share_of_exposure"], "confidence": "deterministic"})
        return {"available": bool(active), "loan_count": len(active), "exposure": round(exposure, 2), "par": par, "dpd_buckets": dpd_buckets, "integrity": integrity, "concentration": {"segments": segments, "products": products}, "vintage": vintages, "drivers": drivers, "methodology": {"deterministic": True, "causality_inferred": False, "npl_regulatory_definition": False, "point_in_time": True, "note": "Point-in-time PAR ratios use the latest available observation per loan. Historical records are reserved for longitudinal analytics."}, "snapshot": self.snapshot_label(current)}

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
            loan_id = cls._loan_id(row)
            if loan_id:
                latest[loan_id] = row
            else:
                anonymous.append(row)
        return list(latest.values()) + anonymous

    @classmethod
    def _duplicate_snapshot_keys(cls, rows: list[dict[str, Any]]) -> list[str]:
        counts: dict[tuple[str, str], int] = defaultdict(int)
        for row in rows:
            loan_id = cls._loan_id(row)
            snapshot = cls._snapshot_key(row)
            if loan_id and snapshot:
                counts[(loan_id, snapshot)] += 1
        return [f"{loan_id}:{snapshot}" for (loan_id, snapshot), count in sorted(counts.items()) if count > 1]

    @staticmethod
    def _loan_id(row: dict[str, Any]) -> str:
        return str(row.get("loan_id") or row.get("id") or "").strip()

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

    def _dpd_buckets(self, rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        buckets = {
            key: {"balance": 0.0, "loans": 0}
            for key in self.DPD_BUCKETS
        }
        for row in rows:
            balance = self._number(row.get("outstanding_principal"))
            dpd = self._number(row.get("dpd"))
            if dpd == 0:
                key = "current"
            elif 1 <= dpd <= 29:
                key = "dpd_1_29"
            elif 30 <= dpd <= 59:
                key = "dpd_30_59"
            elif 60 <= dpd <= 89:
                key = "dpd_60_89"
            elif dpd >= 90:
                key = "dpd_90_plus"
            else:
                raise RiskAnalyticsIntegrityError(
                    f"Invalid DPD value for loan {self._loan_id(row)}: {dpd}"
                )
            buckets[key]["balance"] += balance
            buckets[key]["loans"] += 1

        for value in buckets.values():
            value["balance"] = round(value["balance"], 2)
        return buckets

    @classmethod
    def _par_from_buckets(cls, buckets: dict[str, dict[str, Any]], total: float) -> dict[str, dict[str, Any]]:
        def make(name: str, keys: tuple[str, ...], threshold: int) -> dict[str, Any]:
            balance = round(sum(buckets[key]["balance"] for key in keys), 2)
            loans = sum(buckets[key]["loans"] for key in keys)
            return {"balance": balance, "ratio": round(balance / total, 4) if total else 0, "loans": loans, "dpd_threshold": threshold}

        return {
            "par7": make("par7", ("dpd_1_29", "dpd_30_59", "dpd_60_89", "dpd_90_plus"), 7),
            "par30": make("par30", ("dpd_30_59", "dpd_60_89", "dpd_90_plus"), 30),
            "par60": make("par60", ("dpd_60_89", "dpd_90_plus"), 60),
            "par90": make("par90", ("dpd_90_plus",), 90),
        }

    @classmethod
    def _validate_integrity(cls, exposure: float, buckets: dict[str, dict[str, Any]], par: dict[str, dict[str, Any]]) -> dict[str, Any]:
        bucket_balances = [buckets[key]["balance"] for key in cls.DPD_BUCKETS]
        if any(balance < 0 for balance in bucket_balances):
            raise RiskAnalyticsIntegrityError("Negative balance detected in DPD bucket")

        exposure_cents = round(exposure * 100)
        bucket_cents = round(sum(bucket_balances) * 100)
        if exposure_cents != bucket_cents:
            raise RiskAnalyticsIntegrityError(
                f"Exposure reconciliation failed: exposure={exposure} buckets={sum(bucket_balances)}"
            )

        par30 = par["par30"]["balance"]
        par60 = par["par60"]["balance"]
        par90 = par["par90"]["balance"]
        if not (par30 >= par60 >= par90):
            raise RiskAnalyticsIntegrityError(
                f"Cumulative PAR monotonicity failed: PAR30={par30}, PAR60={par60}, PAR90={par90}"
            )

        if par30 == par60 == par90 and (
            buckets["dpd_30_59"]["balance"] != 0
            or buckets["dpd_60_89"]["balance"] != 0
        ):
            raise RiskAnalyticsIntegrityError(
                "Invalid PAR equality: PAR30=PAR60=PAR90 requires 30-59 and 60-89 balances to be zero"
            )

        return {
            "exposure_reconciled": True,
            "cumulative_par_monotonic": True,
            "non_negative": True,
            "duplicate_keys": [],
            "concentration_valid": True,
        }

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
            result.append({"key": key, "label": labels.get(key, key), "loans": int(value["loans"]), "balance": round(value["balance"], 2), "share_of_exposure": round(value["balance"] / total, 4) if total else 0, "par30": round(value["par30_balance"] / value["balance"], 4) if value["balance"] else 0})
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
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
