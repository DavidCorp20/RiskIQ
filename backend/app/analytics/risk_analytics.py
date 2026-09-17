from __future__ import annotations

from collections import defaultdict
from typing import Any


class RiskAnalyticsService:
    """Deterministic point-in-time portfolio risk analytics.

    Longitudinal records remain available to migration/history. Point-in-time
    ratios use only the latest available observation per loan so the same credit
    is never counted seven or twelve times just because snapshots were uploaded.
    """

    def analyze(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        current = self.latest_snapshot(rows)
        active = [r for r in current if self._number(r.get("outstanding_principal")) > 0]
        exposure = sum(self._number(r.get("outstanding_principal")) for r in active)
        buckets = {"par7": self._bucket(active, 7, exposure), "par30": self._bucket(active, 30, exposure), "par60": self._bucket(active, 60, exposure), "par90": self._bucket(active, 90, exposure)}
        segments = self._concentration(active, exposure, "segment")
        products = self._concentration(active, exposure, "product_id")
        vintages = self._concentration(active, exposure, "origination_date", vintage=True)
        drivers: list[dict[str, Any]] = []
        for item in segments[:5]:
            if item["par30"] >= 0.08 or item["share_of_exposure"] >= 0.25:
                drivers.append({"id": f"segment:{item['key']}", "title": item.get("label", f"Segmento {item['key']}"), "severity": "high" if item["par30"] >= 0.08 else "medium", "evidence": f"{item['loans']} créditos, {item['share_of_exposure'] * 100:.1f}% de exposición y PAR30 de {item['par30'] * 100:.1f}%.", "exposure_share": item["share_of_exposure"], "confidence": "deterministic"})
        return {"available": bool(active), "loan_count": len(active), "exposure": round(exposure, 2), "par": buckets, "concentration": {"segments": segments, "products": products}, "vintage": vintages, "drivers": drivers, "methodology": {"deterministic": True, "causality_inferred": False, "npl_regulatory_definition": False, "point_in_time": True, "note": "Point-in-time PAR ratios use the latest available observation per loan. Historical records are reserved for longitudinal analytics."}, "snapshot": self.snapshot_label(current)}

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
        balance = sum(self._number(r.get("outstanding_principal")) for r in rows if self._number(r.get("dpd")) >= dpd)
        count = sum(1 for r in rows if self._number(r.get("dpd")) >= dpd)
        return {"balance": round(balance, 2), "ratio": round(balance / total, 4) if total else 0, "loans": count, "dpd_threshold": dpd}

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
            return max(float(value or 0), 0.0)
        except (TypeError, ValueError):
            return 0.0
