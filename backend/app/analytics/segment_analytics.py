from __future__ import annotations

from typing import Any


class SegmentAnalyticsService:
    """Evaluate reusable custom segments against the latest state per credit."""

    @staticmethod
    def _snapshot(row: dict[str, Any]) -> str:
        for key in ("snapshot_date", "snapshot_month", "as_of_date"):
            if row.get(key) not in (None, ""):
                return str(row[key])[:10]
        return ""

    @staticmethod
    def _loan(row: dict[str, Any]) -> str:
        return str(row.get("loan_id") or row.get("id") or "").strip()

    @classmethod
    def latest(cls, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        dated = [r for r in rows if cls._snapshot(r)]
        if dated:
            latest_date = max(cls._snapshot(r) for r in dated)
            rows = [r for r in rows if cls._snapshot(r) == latest_date]
        by_loan: dict[str, dict[str, Any]] = {}
        undated: list[dict[str, Any]] = []
        for row in rows:
            loan = cls._loan(row)
            if loan:
                by_loan[loan] = row
            else:
                undated.append(row)
        return list(by_loan.values()) if by_loan else undated

    @staticmethod
    def matches(row: dict[str, Any], condition: dict[str, Any]) -> bool:
        field = str(condition.get("field") or "")
        operator = str(condition.get("operator") or "=")
        target = condition.get("value")
        if not field:
            return True
        value = row.get(field)
        if operator == "is_empty":
            return value is None or str(value).strip() == ""
        if operator == "is_not_empty":
            return value is not None and str(value).strip() != ""
        if operator == "contains":
            return str(target or "").lower() in str(value or "").lower()
        try:
            left, right = float(value), float(target)
        except (TypeError, ValueError):
            left, right = str(value or ""), str(target or "")
        return {"=": left == right, "!=": left != right, ">": left > right, ">=": left >= right, "<": left < right, "<=": left <= right}.get(operator, False)

    @classmethod
    def calculate(cls, rows: list[dict[str, Any]], conditions: list[dict[str, Any]]) -> dict[str, Any]:
        current = [r for r in cls.latest(rows) if all(cls.matches(r, c) for c in conditions)]
        balance_field = next((k for k in ("outstanding_principal", "outstanding_balance", "balance", "ead") if any(r.get(k) not in (None, "") for r in current)), "")
        exposure = sum(float(r.get(balance_field) or 0) for r in current) if balance_field else 0.0
        dpd_field = "dpd" if any(r.get("dpd") not in (None, "") for r in current) else "days_past_due"
        bad30 = sum(float(r.get(balance_field) or 0) for r in current if float(r.get(dpd_field) or 0) >= 30) if balance_field else 0.0
        bad90 = sum(float(r.get(balance_field) or 0) for r in current if float(r.get(dpd_field) or 0) >= 90) if balance_field else 0.0
        return {"loan_count": len(current), "exposure": round(exposure, 2), "par30": round(bad30 / exposure, 4) if exposure else 0.0, "par90": round(bad90 / exposure, 4) if exposure else 0.0, "balance_field": balance_field, "snapshot_date": cls._snapshot(current[0]) if current else None}

    def analyze(self, rows: list[dict[str, Any]], segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{**segment, "analytics": self.calculate(rows, segment.get("conditions") or [])} for segment in segments if segment.get("active", True)]
