from __future__ import annotations

from collections import defaultdict
from typing import Any


class RiskAnalyticsService:
    """Deterministic portfolio risk analytics from canonical portfolio records."""

    def analyze(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        active = [r for r in rows if self._number(r.get("outstanding_principal")) > 0]
        exposure = sum(self._number(r.get("outstanding_principal")) for r in active)
        buckets = {"par7": self._bucket(active, 7, exposure), "par30": self._bucket(active, 30, exposure), "par60": self._bucket(active, 60, exposure), "par90": self._bucket(active, 90, exposure)}
        segments = self._concentration(active, exposure, "segment")
        products = self._concentration(active, exposure, "product_id")
        vintages = self._concentration(active, exposure, "origination_date", vintage=True)
        drivers: list[dict[str, Any]] = []
        for item in segments[:5]:
            if item["par30"] >= 0.08 or item["share_of_exposure"] >= 0.25:
                drivers.append({"id": f"segment:{item['key']}", "title": item.get("label", f"Segmento {item['key']}"), "severity": "high" if item["par30"] >= 0.08 else "medium", "evidence": f"{item['loans']} créditos, {item['share_of_exposure'] * 100:.1f}% de exposición y PAR30 de {item['par30'] * 100:.1f}%.", "exposure_share": item["share_of_exposure"], "confidence": "deterministic"})
        return {"available": bool(active), "loan_count": len(active), "exposure": round(exposure, 2), "par": buckets, "concentration": {"segments": segments, "products": products}, "vintage": vintages, "drivers": drivers, "methodology": {"deterministic": True, "causality_inferred": False, "npl_regulatory_definition": False, "note": "PAR ratios use outstanding principal of records with DPD at or above each threshold."}}

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
            product = str(row.get("product_id") or "").strip()
            if product:
                return f"product:{product}", f"Producto {product}"
            return "Unknown", "Segmento Unknown"
        key = str(row.get(field) or "Unknown").strip() or "Unknown"
        return key, key

    @staticmethod
    def _number(value: Any) -> float:
        try:
            return max(float(value or 0), 0.0)
        except (TypeError, ValueError):
            return 0.0
