from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from statistics import median
from typing import Any

from pydantic import BaseModel, Field

from app.data.canonical import CANONICAL_FIELDS
from app.services.ingestion.semantic_mapper import normalize_name


class QualityIssue(BaseModel):
    code: str
    severity: str
    message: str
    count: int = 1
    field: str | None = None
    rows: list[int] = Field(default_factory=list)


class QualityResult(BaseModel):
    quality_score: float
    status: str
    row_count: int
    column_count: int
    issue_count: int
    issues: list[QualityIssue]
    checks: dict[str, Any]
    analysis_readiness: dict[str, Any]
    policy: str = "El motor determinístico calcula la calidad; la IA puede interpretar los hallazgos, pero no cambia el score."


class DataQualityEngine:
    """Deterministic data-quality gate for portfolio risk analytics."""

    NUMERIC_FIELDS = {
        field for field, meta in CANONICAL_FIELDS.items() if meta.get("type") == "numeric"
    }
    DATE_FIELDS = {
        field for field, meta in CANONICAL_FIELDS.items() if meta.get("type") == "date"
    }

    DATE_ALIASES = {
        "payment_date": {"payment_date", "fecha_pago", "fecha_pago_real", "pago_fecha"},
        "origination_date": {"origination_date", "fecha_desembolso", "fecha_otorgamiento", "fecha_apertura"},
    }
    RATE_ALIASES = {
        "interest_rate", "tasa_interes", "tasa_de_interes", "interest", "rate", "tasa"
    }

    def assess(
        self,
        rows: list[dict[str, Any]],
        *,
        mappings: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not rows:
            return QualityResult(
                quality_score=0,
                status="blocked",
                row_count=0,
                column_count=0,
                issue_count=1,
                issues=[QualityIssue(code="EMPTY_DATASET", severity="critical", message="El dataset está vacío.")],
                checks={"completeness": 0, "validity": 0},
                analysis_readiness={},
            ).model_dump()

        columns = list(dict.fromkeys(key for row in rows for key in row))
        source_to_target = {
            str(item.get("source")): str(item.get("target"))
            for item in (mappings or [])
            if item.get("source") and item.get("target")
        }
        canonical_rows = [
            {source_to_target.get(key, key): value for key, value in row.items()}
            for row in rows
        ]

        issues: list[QualityIssue] = []
        issue_counts: Counter[tuple[str, str, str | None]] = Counter()
        issue_rows: dict[tuple[str, str, str | None], list[int]] = {}
        invalid_cells = 0
        empty_cells = 0
        total_cells = max(1, len(rows) * len(columns))

        def add(
            code: str,
            severity: str,
            message: str,
            *,
            field: str | None = None,
            row_index: int | None = None,
        ) -> None:
            key = (code, severity, field)
            issue_counts[key] += 1
            if row_index is not None:
                issue_rows.setdefault(key, []).append(row_index)

        for index, row in enumerate(canonical_rows):
            for field, value in row.items():
                if value in (None, ""):
                    empty_cells += 1
                    continue

                if field in self.NUMERIC_FIELDS:
                    if self._to_float(value) is None:
                        invalid_cells += 1
                        add(
                            f"INVALID_NUMBER_{field.upper()}",
                            "high",
                            f"El campo {field} contiene un valor no numérico.",
                            field=field,
                            row_index=index,
                        )
                        continue

                    numeric = float(self._to_float(value))
                    if field == "dpd" and numeric < 0:
                        add("NEGATIVE_DPD", "high", "Los días de mora no pueden ser negativos.", field=field, row_index=index)
                    elif field in {"outstanding_principal", "scheduled_amount", "paid_amount", "ead"} and numeric < 0:
                        add("NEGATIVE_BALANCE", "high", "Los importes financieros no pueden ser negativos.", field=field, row_index=index)
                    elif field in {"pd", "lgd"} and not 0 <= numeric <= 1:
                        add(f"INVALID_{field.upper()}_RANGE", "high", f"{field.upper()} debe estar entre 0 y 1.", field=field, row_index=index)

                if field in self.DATE_FIELDS and not self._valid_date(value):
                    invalid_cells += 1
                    add(
                        f"INVALID_DATE_{field.upper()}",
                        "high",
                        f"El campo {field} contiene una fecha inválida.",
                        field=field,
                        row_index=index,
                    )

            loan_id = row.get("loan_id")
            customer_id = row.get("customer_id")
            if loan_id in (None, ""):
                add("MISSING_LOAN_ID", "critical", "Falta loan_id.", field="loan_id", row_index=index)
            if customer_id in (None, ""):
                add("MISSING_CUSTOMER_ID", "critical", "Falta customer_id.", field="customer_id", row_index=index)

            # Interest-rate columns are optional source-specific fields. They are
            # validated deterministically when their header clearly denotes a rate.
            for source_field, source_value in row.items():
                if normalize_name(source_field) not in {normalize_name(alias) for alias in self.RATE_ALIASES}:
                    continue
                rate = self._to_float(source_value)
                if rate is None:
                    invalid_cells += 1
                    add(
                        "INVALID_INTEREST_RATE",
                        "high",
                        "La tasa de interés no es numérica.",
                        field=source_field,
                        row_index=index,
                    )
                elif not 0 <= rate <= 100:
                    add(
                        "INTEREST_RATE_OUT_OF_RANGE",
                        "high",
                        "La tasa de interés debe estar entre 0% y 100% (o su equivalente decimal).",
                        field=source_field,
                        row_index=index,
                    )

            scheduled = self._to_float(row.get("scheduled_amount"))
            paid = self._to_float(row.get("paid_amount"))
            if scheduled is not None and paid is not None and scheduled > 0 and paid > scheduled * 1.05:
                add(
                    "PAID_ABOVE_SCHEDULED",
                    "medium",
                    "El pago supera en más de 5% el monto programado.",
                    field="paid_amount",
                    row_index=index,
                )

            self._date_relationships(row, index, add)

        self._check_uniqueness(canonical_rows, add)
        self._check_outliers(canonical_rows, add)

        issues = [
            QualityIssue(
                code=code,
                severity=severity,
                field=field,
                message=self._message_for(code, field, fallback="Inconsistencia detectada."),
                count=count,
                rows=issue_rows.get((code, severity, field), [])[:50],
            )
            for (code, severity, field), count in sorted(issue_counts.items())
        ]

        critical = sum(i.count for i in issues if i.severity == "critical")
        high = sum(i.count for i in issues if i.severity == "high")
        medium = sum(i.count for i in issues if i.severity == "medium")
        completeness = max(0.0, 1.0 - empty_cells / total_cells)
        validity = max(0.0, 1.0 - invalid_cells / total_cells)
        penalty = min(100.0, critical * 5 + high * 2 + medium * 0.5)
        score = round(max(0.0, completeness * 60 + validity * 40 - penalty), 1)

        mapped_targets = set(source_to_target.values()) | {
            field for field in CANONICAL_FIELDS if field in columns
        }
        required = {
            field for field, meta in CANONICAL_FIELDS.items() if meta.get("required")
        }
        missing_required = sorted(required - mapped_targets)

        readiness = self._analysis_readiness(canonical_rows)
        if missing_required:
            for field in missing_required:
                readiness.setdefault("Portfolio Foundation", {
                    "ready": False,
                    "missing_fields": [],
                })["missing_fields"].append(field)
            add("MISSING_CANONICAL_FIELD", "critical", "Falta un campo canónico requerido.", field=",".join(missing_required))

        status = "blocked" if critical or missing_required else ("warning" if score < 80 else "passed")

        return QualityResult(
            quality_score=score,
            status=status,
            row_count=len(rows),
            column_count=len(columns),
            issue_count=sum(i.count for i in issues) + len(missing_required),
            issues=issues,
            checks={
                "completeness": round(completeness, 4),
                "validity": round(validity, 4),
                "duplicate_snapshot_loan_keys": self._duplicate_key_count(canonical_rows),
                "outlier_checks": ["outstanding_principal", "dpd", "paid_amount"],
                "date_relationship_checks": ["payment_date >= origination_date", "due_date >= origination_date"],
            },
            analysis_readiness=readiness,
        ).model_dump()

    def _date_relationships(self, row: dict[str, Any], index: int, add: Any) -> None:
        origination = self._parse_date(row.get("origination_date"))
        payment = self._find_date(row, "payment_date")
        due = self._parse_date(row.get("due_date"))

        if origination and payment and payment < origination:
            add(
                "PAYMENT_BEFORE_ORIGINATION",
                "high",
                "payment_date es anterior a origination_date.",
                field="payment_date",
                row_index=index,
            )
        if origination and due and due < origination:
            add(
                "DUE_BEFORE_ORIGINATION",
                "high",
                "due_date es anterior a origination_date.",
                field="due_date",
                row_index=index,
            )

    def _check_uniqueness(self, rows: list[dict[str, Any]], add: Any) -> None:
        keys: list[tuple[str, str]] = []
        has_snapshot = any(row.get("snapshot_date") not in (None, "") for row in rows)
        for index, row in enumerate(rows):
            loan_id = row.get("loan_id")
            snapshot = row.get("snapshot_date")
            if loan_id in (None, ""):
                continue
            key = (str(loan_id), str(snapshot)) if has_snapshot else (str(loan_id), "")
            keys.append(key)

        counts = Counter(keys)
        for (loan_id, snapshot), count in counts.items():
            if count > 1:
                add(
                    "DUPLICATE_SNAPSHOT_LOAN",
                    "critical",
                    "La combinación loan_id + snapshot_date no es única.",
                    field="loan_id",
                )

    def _check_outliers(self, rows: list[dict[str, Any]], add: Any) -> None:
        for field in ("outstanding_principal", "dpd", "paid_amount"):
            values = [
                float(value)
                for row in rows
                if (value := self._to_float(row.get(field))) is not None
            ]
            if len(values) < 8:
                continue
            q1, q3 = self._quartiles(values)
            iqr = q3 - q1
            if iqr <= 0:
                continue
            lower, upper = q1 - 3 * iqr, q3 + 3 * iqr
            for index, row in enumerate(rows):
                value = self._to_float(row.get(field))
                if value is not None and (value < lower or value > upper):
                    add(
                        f"OUTLIER_{field.upper()}",
                        "medium",
                        f"Valor atípico detectado en {field} mediante IQR robusto.",
                        field=field,
                        row_index=index,
                    )

    @staticmethod
    def _quartiles(values: list[float]) -> tuple[float, float]:
        ordered = sorted(values)
        n = len(ordered)
        mid = n // 2
        lower = ordered[:mid]
        upper = ordered[mid + (n % 2):]
        return median(lower), median(upper)

    def _analysis_readiness(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        def present(field: str) -> bool:
            return any(row.get(field) not in (None, "") for row in rows)

        models = {
            "Portfolio Health": ["loan_id", "outstanding_principal"],
            "Delinquency Analysis": ["loan_id", "dpd", "outstanding_principal"],
            "Concentration Analysis": ["loan_id", "segment", "outstanding_principal"],
            "Vintage Analysis": ["loan_id", "origination_date", "dpd", "outstanding_principal"],
            "Migration / Roll Rate": ["loan_id", "snapshot_date", "dpd", "outstanding_principal"],
        }
        return {
            name: {
                "ready": not missing,
                "missing_fields": missing,
            }
            for name, required in models.items()
            if not (missing := [field for field in required if not present(field)])
        } | {
            name: {
                "ready": False,
                "missing_fields": [field for field in required if not present(field)],
            }
            for name, required in models.items()
            if [field for field in required if not present(field)]
        }

    @staticmethod
    def _duplicate_key_count(rows: list[dict[str, Any]]) -> int:
        keys = [
            (str(row.get("loan_id")), str(row.get("snapshot_date")))
            for row in rows
            if row.get("loan_id") not in (None, "")
        ]
        return sum(max(0, count - 1) for count in Counter(keys).values())

    @classmethod
    def _find_date(cls, row: dict[str, Any], canonical_name: str) -> date | None:
        value = row.get(canonical_name)
        if value not in (None, ""):
            return cls._parse_date(value)
        aliases = cls.DATE_ALIASES.get(canonical_name, set())
        for key, candidate in row.items():
            if normalize_name(key) in {normalize_name(alias) for alias in aliases}:
                return cls._parse_date(candidate)
        return None

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        text = str(value).strip()
        for parser in (date.fromisoformat, lambda v: datetime.fromisoformat(v).date()):
            try:
                return parser(text)
            except (TypeError, ValueError):
                pass
        return None

    @classmethod
    def _valid_date(cls, value: Any) -> bool:
        return cls._parse_date(value) is not None

    @staticmethod
    def _to_float(value: Any) -> float | None:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _message_for(code: str, field: str | None, fallback: str) -> str:
        known = {
            "MISSING_LOAN_ID": "Falta el identificador del crédito.",
            "MISSING_CUSTOMER_ID": "Falta el identificador del cliente.",
            "DUPLICATE_SNAPSHOT_LOAN": "La combinación loan_id + snapshot_date se repite.",
            "PAYMENT_BEFORE_ORIGINATION": "La fecha de pago es anterior a la originación.",
            "DUE_BEFORE_ORIGINATION": "La fecha de vencimiento es anterior a la originación.",
            "PAID_ABOVE_SCHEDULED": "El monto pagado supera materialmente el monto programado.",
            "NEGATIVE_DPD": "Los días de mora no pueden ser negativos.",
            "NEGATIVE_BALANCE": "El saldo o importe financiero no puede ser negativo.",
        }
        return known.get(code, f"{fallback} Campo: {field}." if field else fallback)


# Compatibility alias for future callers.
DataQualityService = DataQualityEngine
