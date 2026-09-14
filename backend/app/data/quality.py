from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Any

from app.data.canonical import CANONICAL_FIELDS


class DataQualityService:
    """Deterministic quality assessment with row, column and analysis-impact evidence."""

    NUMERIC_FIELDS = {field for field, meta in CANONICAL_FIELDS.items() if meta.get("type") == "numeric"}
    DATE_FIELDS = {field for field, meta in CANONICAL_FIELDS.items() if meta.get("type") == "date"}

    def assess(self, rows: list[dict[str, Any]], *, mappings: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        if not rows:
            return {"quality_score": 0, "status": "blocked", "row_count": 0, "column_count": 0, "issue_count": 1, "issues": [{"code": "EMPTY_DATASET", "severity": "critical", "count": 1}], "row_issues": [], "column_issues": [], "analysis_impacts": []}

        issues: Counter[tuple[str, str]] = Counter()
        row_issues: list[dict[str, Any]] = []
        field_stats: dict[str, dict[str, Any]] = {}
        duplicate_ids: set[str] = set()
        seen_ids: dict[str, int] = {}
        columns = list(dict.fromkeys(key for row in rows for key in row))
        mapped = {item.get("source"): item.get("target") for item in (mappings or []) if item.get("source") and item.get("target")}

        def add_row_issue(row_index: int, code: str, severity: str, field: str | None, message: str) -> None:
            issues[(code, severity)] += 1
            row_issues.append({"row": row_index, "field": field, "code": code, "severity": severity, "message": message})

        for index, row in enumerate(rows):
            canonical_row = {mapped.get(key, key): value for key, value in row.items()}
            for field, value in row.items():
                stats = field_stats.setdefault(field, {"present": 0, "empty": 0, "invalid": 0})
                if value in (None, ""):
                    stats["empty"] += 1
                else:
                    stats["present"] += 1

            loan_id = canonical_row.get("loan_id")
            if loan_id in (None, ""):
                add_row_issue(index, "MISSING_LOAN_ID", "critical", next((source for source, target in mapped.items() if target == "loan_id"), "loan_id"), "Falta el identificador del crédito/cuenta.")
            else:
                key = str(loan_id)
                seen_ids[key] = seen_ids.get(key, 0) + 1
                if seen_ids[key] > 1:
                    duplicate_ids.add(key)
                    add_row_issue(index, "DUPLICATE_LOAN_ID", "critical", next((source for source, target in mapped.items() if target == "loan_id"), "loan_id"), "El identificador del crédito aparece más de una vez.")

            if canonical_row.get("customer_id") in (None, ""):
                add_row_issue(index, "MISSING_CUSTOMER_ID", "critical", next((source for source, target in mapped.items() if target == "customer_id"), "customer_id"), "Falta el identificador del cliente.")

            for field in self.NUMERIC_FIELDS:
                if field not in canonical_row or canonical_row[field] in (None, ""):
                    continue
                try:
                    value = float(canonical_row[field])
                    if field == "dpd" and value < 0:
                        add_row_issue(index, "NEGATIVE_DPD", "high", next((source for source, target in mapped.items() if target == field), field), "Los días de mora no pueden ser negativos.")
                    elif field in {"outstanding_principal", "scheduled_amount", "paid_amount", "ead"} and value < 0:
                        add_row_issue(index, f"NEGATIVE_{field.upper()}", "high", next((source for source, target in mapped.items() if target == field), field), "El valor monetario no puede ser negativo.")
                    elif field in {"pd", "lgd"} and not 0 <= value <= 1:
                        add_row_issue(index, f"INVALID_{field.upper()}_RANGE", "high", next((source for source, target in mapped.items() if target == field), field), "El indicador debe estar entre 0 y 1.")
                except (TypeError, ValueError):
                    field_stats.setdefault(field, {"present": 0, "empty": 0, "invalid": 0})["invalid"] += 1
                    add_row_issue(index, f"INVALID_NUMBER_{field.upper()}", "high", next((source for source, target in mapped.items() if target == field), field), "El valor no es numérico.")

            for field in self.DATE_FIELDS:
                if field in canonical_row and canonical_row[field] not in (None, "") and not self._valid_date(canonical_row[field]):
                    field_stats.setdefault(field, {"present": 0, "empty": 0, "invalid": 0})["invalid"] += 1
                    add_row_issue(index, f"INVALID_DATE_{field.upper()}", "high", next((source for source, target in mapped.items() if target == field), field), "La fecha no tiene un formato válido.")

            scheduled = self._number(canonical_row.get("scheduled_amount"))
            paid = self._number(canonical_row.get("paid_amount"))
            if scheduled > 0 and paid > scheduled * 1.05:
                add_row_issue(index, "PAID_ABOVE_SCHEDULED", "medium", next((source for source, target in mapped.items() if target == "paid_amount"), "paid_amount"), "El pago supera en más de 5% al monto programado.")

        total_cells = max(1, len(rows) * max(1, len(columns)))
        empty_cells = sum(stats["empty"] for stats in field_stats.values())
        invalid_cells = sum(stats["invalid"] for stats in field_stats.values())
        completeness = max(0.0, 1.0 - empty_cells / total_cells)
        validity = max(0.0, 1.0 - invalid_cells / total_cells)
        critical = sum(count for (_, severity), count in issues.items() if severity == "critical")
        high = sum(count for (_, severity), count in issues.items() if severity == "high")
        medium = sum(count for (_, severity), count in issues.items() if severity == "medium")
        penalty = min(100.0, critical * 5 + high * 2 + medium * 0.5)
        score = round(max(0.0, completeness * 60 + validity * 40 - penalty), 1)
        status = "blocked" if critical else ("warning" if score < 80 else "passed")

        column_issues = []
        for field, stats in field_stats.items():
            missing_rate = stats["empty"] / max(1, len(rows))
            invalid_rate = stats["invalid"] / max(1, len(rows))
            if missing_rate >= 0.1 or invalid_rate > 0:
                column_issues.append({"field": field, "missing_rate": round(missing_rate, 4), "invalid_rate": round(invalid_rate, 4), "severity": "warning"})

        issues_list = [{"code": code, "severity": severity, "count": count} for (code, severity), count in sorted(issues.items())]
        impacts = self._analysis_impacts(rows, columns, mapped)
        return {
            "quality_score": score,
            "status": status,
            "row_count": len(rows),
            "column_count": len(columns),
            "issue_count": sum(item["count"] for item in issues_list),
            "issues": issues_list,
            "row_issues": row_issues[:500],
            "row_issue_truncated": len(row_issues) > 500,
            "column_issues": column_issues,
            "analysis_impacts": impacts,
            "checks": {"completeness": round(completeness, 4), "validity": round(validity, 4), "unique_loan_ids": len([value for value in seen_ids if seen_ids[value] == 1]), "duplicate_loan_ids": len(duplicate_ids)},
            "mapping": {"provided": mappings is not None, "mapped_fields": len(mappings or []), "canonical_targets": sorted(set(mapped.values()))},
            "policy": "Errors block affected analysis; warnings remain processable and are surfaced with their analytical impact.",
        }

    @staticmethod
    def _analysis_impacts(rows: list[dict[str, Any]], columns: list[str], mappings: dict[str, str]) -> list[dict[str, Any]]:
        canonical_columns = set(columns) | set(mappings.values())
        def has(field: str) -> bool:
            if field not in canonical_columns:
                return False
            source_fields = [field] + [source for source, target in mappings.items() if target == field]
            return any(any(row.get(source) not in (None, "") for row in rows) for source in source_fields)
        impacts = []
        for model, requires, label in [
            ("Portfolio Health", ["dpd", "outstanding_principal"], "Diagnóstico principal de cartera"),
            ("Delinquency Analysis", ["dpd", "outstanding_principal"], "Distribución y concentración de mora"),
            ("Concentration Analysis", ["segment", "outstanding_principal", "dpd"], "Concentración por segmento"),
            ("Vintage Analysis", ["origination_date", "dpd", "outstanding_principal"], "Desempeño por cohorte"),
            ("Migration / Roll Rate", ["loan_id", "snapshot_date", "dpd", "outstanding_principal"], "Movimiento entre estados de mora"),
        ]:
            missing = [field for field in requires if not has(field)]
            impacts.append({"model": model, "label": label, "ready": not missing, "missing_fields": missing, "severity": "none" if not missing else ("warning" if model in {"Vintage Analysis", "Migration / Roll Rate"} else "blocking")})
        return impacts

    @staticmethod
    def _number(value: Any) -> float:
        try:return float(value or 0)
        except (TypeError, ValueError):return 0.0

    @staticmethod
    def _valid_date(value: Any) -> bool:
        if isinstance(value, (date, datetime)):return True
        for parser in (datetime.fromisoformat, date.fromisoformat):
            try: parser(str(value)); return True
            except ValueError: continue
        return False
