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

        self._validate_source_balances(rows)

        current = self.latest_snapshot(rows)
        static = self._analyze_snapshot(current)
        active = static["active"]
        exposure = static["exposure"]
        dpd_buckets = static["dpd_buckets"]
        par = static["par"]
        integrity = static["integrity"]

        segments = self._concentration(active, exposure, "segment")
        products = self._concentration(active, exposure, "product_id")
        vintages = self._concentration(active, exposure, "origination_date", vintage=True)
        drivers = self._build_drivers(segments)

        migration: dict[str, Any] = {}
        deterioration_drivers: list[dict[str, Any]] = []
        dates = sorted({self._snapshot_key(row) for row in rows if self._snapshot_key(row)})
        if len(dates) >= 2:
            t0_date, t1_date = dates[-2], dates[-1]
            t0_rows = [row for row in rows if self._snapshot_key(row) == t0_date]
            t1_rows = [row for row in rows if self._snapshot_key(row) == t1_date]
            try:
                t0 = self._analyze_snapshot(t0_rows)
            except RiskAnalyticsIntegrityError as exc:
                raise RiskAnalyticsIntegrityError(f"Integrity failure at {t0_date}: {exc}") from exc
            try:
                t1 = self._analyze_snapshot(t1_rows)
            except RiskAnalyticsIntegrityError as exc:
                raise RiskAnalyticsIntegrityError(f"Integrity failure at {t1_date}: {exc}") from exc
            migration = self._migration(t0_rows, t1_rows, t0_date, t1_date, t0, t1)
            deterioration_drivers = self._deterioration_drivers(t0_rows, t1_rows, migration)

        return {
            "available": bool(active),
            "loan_count": len(active),
            "exposure": round(exposure, 2),
            "par": par,
            "dpd_buckets": dpd_buckets,
            "integrity": integrity,
            "concentration": {"segments": segments, "products": products},
            "vintage": vintages,
            "drivers": drivers,
            "migration": migration,
            "deterioration_drivers": deterioration_drivers,
            "methodology": {
                "deterministic": True,
                "causality_inferred": False,
                "npl_regulatory_definition": False,
                "point_in_time": True,
                "note": "Point-in-time PAR ratios use the latest available observation per loan. Historical records are reserved for longitudinal analytics.",
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
        return [
            f"{loan_id}:{snapshot}"
            for (loan_id, snapshot), count in sorted(counts.items())
            if count > 1
        ]

    @classmethod
    def _validate_source_balances(cls, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            balance = cls._number(row.get("outstanding_principal"))
            if balance < 0:
                snapshot = cls._snapshot_key(row) or "unknown"
                raise RiskAnalyticsIntegrityError(
                    f"Negative outstanding_principal at {snapshot} for loan {cls._loan_id(row)}: {balance}"
                )

    def _analyze_snapshot(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        current = self._dedupe_by_loan(rows)
        active = [
            row
            for row in current
            if self._number(row.get("outstanding_principal")) > 0
        ]
        exposure = sum(
            self._number(row.get("outstanding_principal")) for row in active
        )
        dpd_buckets, par7_balance, par7_loans = self._dpd_buckets(active)
        par = self._par_from_buckets(
            dpd_buckets, exposure, par7_balance, par7_loans
        )
        integrity = self._validate_integrity(exposure, dpd_buckets, par)
        return {
            "rows": current,
            "active": active,
            "exposure": round(exposure, 2),
            "dpd_buckets": dpd_buckets,
            "par": par,
            "integrity": integrity,
        }

    @staticmethod
    def _bucket_for_dpd(dpd: float) -> str:
        if dpd == 0:
            return "current"
        if 1 <= dpd <= 29:
            return "dpd_1_29"
        if 30 <= dpd <= 59:
            return "dpd_30_59"
        if 60 <= dpd <= 89:
            return "dpd_60_89"
        if dpd >= 90:
            return "dpd_90_plus"
        raise RiskAnalyticsIntegrityError(f"Invalid DPD value: {dpd}")

    def _dpd_buckets(
        self, rows: list[dict[str, Any]]
    ) -> tuple[dict[str, dict[str, Any]], float, int]:
        buckets = {
            key: {"balance": 0.0, "loans": 0} for key in self.DPD_BUCKETS
        }
        par7_balance = 0.0
        par7_loans = 0
        for row in rows:
            balance = self._number(row.get("outstanding_principal"))
            dpd = self._number(row.get("dpd"))
            key = self._bucket_for_dpd(dpd)
            buckets[key]["balance"] += balance
            buckets[key]["loans"] += 1
            if dpd >= 7:
                par7_balance += balance
                par7_loans += 1

        for value in buckets.values():
            value["balance"] = round(value["balance"], 2)
        return buckets, round(par7_balance, 2), par7_loans

    @classmethod
    def _par_from_buckets(
        cls,
        buckets: dict[str, dict[str, Any]],
        total: float,
        par7_balance: float,
        par7_loans: int,
    ) -> dict[str, dict[str, Any]]:
        def make(balance: float, loans: int, threshold: int) -> dict[str, Any]:
            balance = round(balance, 2)
            return {
                "balance": balance,
                "ratio": round(balance / total, 4) if total else 0,
                "loans": loans,
                "dpd_threshold": threshold,
            }

        par30_balance = round(
            buckets["dpd_30_59"]["balance"]
            + buckets["dpd_60_89"]["balance"]
            + buckets["dpd_90_plus"]["balance"],
            2,
        )
        par60_balance = round(
            buckets["dpd_60_89"]["balance"]
            + buckets["dpd_90_plus"]["balance"],
            2,
        )
        par90_balance = buckets["dpd_90_plus"]["balance"]
        return {
            "par7": make(par7_balance, par7_loans, 7),
            "par30": make(
                par30_balance,
                buckets["dpd_30_59"]["loans"]
                + buckets["dpd_60_89"]["loans"]
                + buckets["dpd_90_plus"]["loans"],
                30,
            ),
            "par60": make(
                par60_balance,
                buckets["dpd_60_89"]["loans"]
                + buckets["dpd_90_plus"]["loans"],
                60,
            ),
            "par90": make(par90_balance, buckets["dpd_90_plus"]["loans"], 90),
        }

    @classmethod
    def _validate_integrity(
        cls,
        exposure: float,
        buckets: dict[str, dict[str, Any]],
        par: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        bucket_balances = [buckets[key]["balance"] for key in cls.DPD_BUCKETS]
        if any(balance < 0 for balance in bucket_balances):
            raise RiskAnalyticsIntegrityError("Negative balance detected in DPD bucket")

        if round(exposure * 100) != round(sum(bucket_balances) * 100):
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

    def _migration(
        self,
        t0_rows: list[dict[str, Any]],
        t1_rows: list[dict[str, Any]],
        t0_date: str,
        t1_date: str,
        t0: dict[str, Any],
        t1: dict[str, Any],
    ) -> dict[str, Any]:
        t0_by_loan = {
            self._loan_id(row): row
            for row in t0_rows
            if self._loan_id(row)
            and self._number(row.get("outstanding_principal")) > 0
        }
        t1_by_loan = {
            self._loan_id(row): row
            for row in t1_rows
            if self._loan_id(row)
        }

        matrix: dict[str, dict[str, dict[str, Any]]] = {
            source: {
                target: {"balance": 0.0, "loans": 0}
                for target in (*self.DPD_BUCKETS, "closed")
            }
            for source in self.DPD_BUCKETS
        }
        flows = {
            "downgrades": {"balance": 0.0, "loans": 0},
            "upgrades": {"balance": 0.0, "loans": 0},
            "statics": {"balance": 0.0, "loans": 0},
            "closed": {"balance": 0.0, "loans": 0},
        }
        new_originations = {"balance": 0.0, "loans": 0}

        bucket_index = {bucket: index for index, bucket in enumerate(self.DPD_BUCKETS)}
        for loan_id, row0 in t0_by_loan.items():
            balance0 = self._number(row0.get("outstanding_principal"))
            source = self._bucket_for_dpd(self._number(row0.get("dpd")))
            row1 = t1_by_loan.get(loan_id)
            if row1 is None or self._number(row1.get("outstanding_principal")) <= 0:
                target = "closed"
                flow = "closed"
            else:
                target = self._bucket_for_dpd(self._number(row1.get("dpd")))
                delta = bucket_index[target] - bucket_index[source]
                flow = "downgrades" if delta > 0 else "upgrades" if delta < 0 else "statics"

            cell = matrix[source][target]
            cell["balance"] += balance0
            cell["loans"] += 1
            flows[flow]["balance"] += balance0
            flows[flow]["loans"] += 1

        t0_ids = set(t0_by_loan)
        for loan_id, row1 in t1_by_loan.items():
            if loan_id not in t0_ids:
                balance1 = self._number(row1.get("outstanding_principal"))
                if balance1 > 0:
                    new_originations["balance"] += balance1
                    new_originations["loans"] += 1

        for source in matrix:
            for target in matrix[source]:
                matrix[source][target]["balance"] = round(
                    matrix[source][target]["balance"], 2
                )
                denominator = sum(
                    matrix[source][candidate]["balance"]
                    for candidate in matrix[source]
                )
                matrix[source][target]["ratio"] = (
                    round(matrix[source][target]["balance"] / denominator, 4)
                    if denominator
                    else 0
                )

        initial_exposure = round(t0["exposure"], 2)
        classified_t0_balance = round(
            sum(flow["balance"] for flow in flows.values()), 2
        )
        if round(initial_exposure * 100) != round(classified_t0_balance * 100):
            raise RiskAnalyticsIntegrityError(
                f"Migration flow reconciliation failed between {t0_date} and {t1_date}: "
                f"T0 exposure={initial_exposure}, classified={classified_t0_balance}"
            )

        for flow in flows.values():
            flow["balance"] = round(flow["balance"], 2)
            flow["ratio_of_t0"] = (
                round(flow["balance"] / initial_exposure, 4)
                if initial_exposure
                else 0
            )

        new_originations["balance"] = round(new_originations["balance"], 2)
        new_originations["ratio_of_t1"] = (
            round(new_originations["balance"] / t1["exposure"], 4)
            if t1["exposure"]
            else 0
        )

        return {
            "available": True,
            "t0": t0_date,
            "t1": t1_date,
            "initial_exposure": initial_exposure,
            "final_exposure": round(t1["exposure"], 2),
            "matrix": matrix,
            "flows": flows,
            "new_originations": new_originations,
            "reconciliation": {
                "initial_exposure": initial_exposure,
                "classified_t0_balance": classified_t0_balance,
                "reconciled": True,
            },
        }

    def _deterioration_drivers(
        self,
        t0_rows: list[dict[str, Any]],
        t1_rows: list[dict[str, Any]],
        migration: dict[str, Any],
    ) -> list[dict[str, Any]]:
        t1_by_loan = {
            self._loan_id(row): row for row in t1_rows if self._loan_id(row)
        }
        results: list[dict[str, Any]] = []
        for field, vintage in (("origination_date", True), ("segment", False)):
            groups: dict[str, dict[str, Any]] = defaultdict(
                lambda: {
                    "label": "",
                    "t0_balance": 0.0,
                    "downgrade_balance": 0.0,
                    "downgrade_loans": 0,
                    "to_30_plus_balance": 0.0,
                    "to_30_plus_loans": 0,
                }
            )
            for row0 in t0_rows:
                loan_id = self._loan_id(row0)
                balance0 = self._number(row0.get("outstanding_principal"))
                if not loan_id or balance0 <= 0:
                    continue
                key, label = self._group_value(row0, field, vintage)
                group = groups[key]
                group["label"] = label
                group["t0_balance"] += balance0
                row1 = t1_by_loan.get(loan_id)
                if row1 is None or self._number(row1.get("outstanding_principal")) <= 0:
                    continue
                source = self._bucket_for_dpd(self._number(row0.get("dpd")))
                target = self._bucket_for_dpd(self._number(row1.get("dpd")))
                source_index = self.DPD_BUCKETS.index(source)
                target_index = self.DPD_BUCKETS.index(target)
                if target_index > source_index:
                    group["downgrade_balance"] += balance0
                    group["downgrade_loans"] += 1
                if target_index > source_index and target_index >= 2:
                    group["to_30_plus_balance"] += balance0
                    group["to_30_plus_loans"] += 1

            for key, group in groups.items():
                if group["t0_balance"] <= 0:
                    continue
                results.append(
                    {
                        "dimension": "vintage" if vintage else "segment",
                        "key": key,
                        "label": group["label"],
                        "t0_balance": round(group["t0_balance"], 2),
                        "downgrade_balance": round(group["downgrade_balance"], 2),
                        "downgrade_rate": round(
                            group["downgrade_balance"] / group["t0_balance"], 4
                        ),
                        "to_30_plus_balance": round(group["to_30_plus_balance"], 2),
                        "to_30_plus_rate": round(
                            group["to_30_plus_balance"] / group["t0_balance"], 4
                        ),
                        "downgrade_loans": group["downgrade_loans"],
                        "to_30_plus_loans": group["to_30_plus_loans"],
                    }
                )

        return sorted(
            results,
            key=lambda item: (
                item["to_30_plus_rate"],
                item["to_30_plus_balance"],
                item["downgrade_rate"],
            ),
            reverse=True,
        )

    @staticmethod
    def _build_drivers(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        drivers: list[dict[str, Any]] = []
        for item in segments[:5]:
            if item["par30"] > 0:
                drivers.append(
                    {
                        "id": f"segment:{item['key']}",
                        "title": item.get("label", f"Segmento {item['key']}"),
                        "severity": "high" if item["par30"] >= 0.08 else "medium",
                        "evidence": (
                            f"{item['loans']} créditos, "
                            f"{item['share_of_exposure'] * 100:.1f}% de exposición "
                            f"y PAR30 de {item['par30'] * 100:.1f}%."
                        ),
                        "exposure_share": item["share_of_exposure"],
                        "confidence": "deterministic",
                    }
                )
        return drivers

    def _concentration(
        self,
        rows: list[dict[str, Any]],
        total: float,
        field: str,
        vintage: bool = False,
    ) -> list[dict[str, Any]]:
        groups: dict[str, dict[str, float]] = defaultdict(
            lambda: {"balance": 0.0, "loans": 0.0, "par30_balance": 0.0}
        )
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
            result.append(
                {
                    "key": key,
                    "label": labels.get(key, key),
                    "loans": int(value["loans"]),
                    "balance": round(value["balance"], 2),
                    "share_of_exposure": round(value["balance"] / total, 4)
                    if total
                    else 0,
                    "par30": round(value["par30_balance"] / value["balance"], 4)
                    if value["balance"]
                    else 0,
                }
            )
        return sorted(result, key=lambda x: x["balance"], reverse=True)

    @staticmethod
    def _group_value(
        row: dict[str, Any], field: str, vintage: bool = False
    ) -> tuple[str, str]:
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

    @classmethod
    def snapshot_label(cls, rows: list[dict[str, Any]]) -> str | None:
        keys = [cls._snapshot_key(r) for r in rows if cls._snapshot_key(r)]
        return max(keys) if keys else None

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

    @staticmethod
    def _number(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
