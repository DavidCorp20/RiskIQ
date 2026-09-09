from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Any


class DataQualityService:
    """Deterministic quality checks for normalized credit portfolio data."""

    REQUIRED_FIELDS = {"customer_id", "loan_id"}
    NUMERIC_FIELDS = {
        "scheduled_amount",
        "paid_amount",
        "outstanding_principal",
        "dpd",
    }
    DATE_FIELDS = {"origination_date", "due_date", "payment_date", "snapshot_date"}

    def assess(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            return {
                "quality_score": 0,
                "status": "blocked",
                "row_count": 0,
                "issue_count": 1,
                "issues": [{"code": "EMPTY_DATASET", "severity": "critical", "count": 1}],
                "checks": {},
            }

        issues: Counter[tuple[str, str]] = Counter()
        field_stats: dict[str, dict[str, Any]] = {}
        duplicate_ids: set[str] = set()
        seen_ids: set[str] = set()

        for row in rows:
            for field, value in row.items():
                stats = field_stats.setdefault(field, {"present": 0, "empty": 0})
                if value in (None, ""):
                    stats["empty"] += 1
                else:
                    stats["present"] += 1

            customer_id = row.get("customer_id")
            loan_id = row.get("loan_id")
            if customer_id in (None, ""):
                issues[("MISSING_CUSTOMER_ID", "critical")] += 1
            if loan_id in (None, ""):
                issues[("MISSING_LOAN_ID", "critical")] += 1
            elif loan_id in seen_ids:
                duplicate_ids.add(str(loan_id))
            else:
                seen_ids.add(loan_id)

            for field in self.NUMERIC_FIELDS:
                if field in row and row[field] not in (None, ""):
                    try:
                        value = float(row[field])
                        if value < 0:
                            issues[(f"NEGATIVE_{field.upper()}", "high")] += 1
                    except (TypeError, ValueError):
                        issues[(f"INVALID_NUMBER_{field.upper()}", "high")] += 1

            for field in self.DATE_FIELDS:
                if field in row and row[field] not in (None, "") and not self._valid_date(row[field]):
                    issues[(f"INVALID_DATE_{field.upper()}", "high")] += 1

            scheduled = self._number(row.get("scheduled_amount"))
            paid = self._number(row.get("paid_amount"))
            if scheduled and paid > scheduled * 1.05:
                issues[("PAID_ABOVE_SCHEDULED", "medium")] += 1

            outstanding = self._number(row.get("outstanding_principal"))
            if outstanding < 0:
                issues[("NEGATIVE_OUTSTANDING_PRINCIPAL", "high")] += 1

        if duplicate_ids:
            issues[("DUPLICATE_LOAN_ID", "critical")] += len(duplicate_ids)

        total_cells = max(1, len(rows) * max(1, len(field_stats)))
        empty_cells = sum(stats["empty"] for stats in field_stats.values())
        completeness = max(0.0, 1.0 - empty_cells / total_cells)

        critical = sum(count for (_, severity), count in issues.items() if severity == "critical")
        high = sum(count for (_, severity), count in issues.items() if severity == "high")
        medium = sum(count for (_, severity), count in issues.items() if severity == "medium")
        penalty = min(100.0, critical * 8 + high * 3 + medium * 1.5)
        score = round(max(0.0, completeness * 100 - penalty), 1)

        if critical:
            status = "blocked"
        elif score < 80:
            status = "warning"
        else:
            status = "passed"

        formatted = [
            {"code": code, "severity": severity, "count": count}
            for (code, severity), count in sorted(issues.items())
        ]
        return {
            "quality_score": score,
            "status": status,
            "row_count": len(rows),
            "issue_count": sum(item["count"] for item in formatted),
            "issues": formatted,
            "checks": {
                "completeness": round(completeness, 4),
                "unique_loan_ids": len(seen_ids),
                "duplicate_loan_ids": len(duplicate_ids),
                "required_fields": sorted(self.REQUIRED_FIELDS),
            },
            "policy": "critical data-quality issues block persistence into the analytical model",
        }

    @staticmethod
    def _number(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _valid_date(value: Any) -> bool:
        if isinstance(value, (date, datetime)):
            return True
        try:
            datetime.fromisoformat(str(value))
            return True
        except ValueError:
            try:
                date.fromisoformat(str(value))
                return True
            except ValueError:
                return False
