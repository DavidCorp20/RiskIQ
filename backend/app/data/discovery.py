from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MappingSuggestion:
    source: str
    target: str
    confidence: float
    matched_alias: str
    required: bool


ALIASES: dict[str, tuple[str, ...]] = {
    "customer_id": ("customer_id", "cliente", "client_id", "customer_number", "id_cliente", "cod_cliente", "identificacion", "identificación", "cedula", "cédula", "dni"),
    "loan_id": ("loan_id", "credito", "crédito", "credit_id", "contrato", "contrato_id", "prestamo", "préstamo", "id_credito", "id_crédito"),
    "product_id": ("product_id", "producto_id", "id_producto", "product", "producto"),
    "origination_date": ("origination_date", "fecha_desembolso", "fecha desembolso", "desembolso", "start_date", "fecha_otorgamiento", "fecha de otorgamiento"),
    "due_date": ("due_date", "fecha_vencimiento", "fecha vencimiento", "vencimiento", "next_due_date"),
    "scheduled_amount": ("scheduled_amount", "cuota", "cuota_programada", "cuota programada", "installment_amount", "monto_cuota"),
    "paid_amount": ("paid_amount", "pagado", "monto_pagado", "amount_paid", "pago", "pagos"),
    "outstanding_principal": ("outstanding_principal", "saldo", "saldo_capital", "outstanding", "outstanding_balance", "balance", "capital_pendiente"),
    "status": ("status", "estado", "estatus", "situacion", "situación"),
    "segment": ("segment", "segmento", "categoria", "categoría", "grupo"),
    "dpd": ("dpd", "dias_mora", "días_mora", "dias mora", "días mora", "days_past_due", "mora"),
}

REQUIRED_FIELDS = {"customer_id", "loan_id"}


def _normalize_name(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9áéíóúüñ]+", "_", value, flags=re.IGNORECASE)
    return re.sub(r"_+", "_", value).strip("_")


def _infer_type(values: list[Any]) -> str:
    non_empty = [v for v in values if v not in (None, "")]
    if not non_empty:
        return "empty"
    if all(isinstance(v, bool) for v in non_empty):
        return "boolean"
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in non_empty):
        return "numeric"
    text = [str(v).strip() for v in non_empty]
    date_like = sum(bool(re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$", v)) for v in text)
    if date_like / len(text) >= 0.8:
        return "date"
    unique_ratio = len(set(text)) / len(text)
    return "categorical" if unique_ratio < 0.2 else "text"


class DataDiscoveryService:
    """Profiles an uploaded dataset and proposes conservative canonical mappings."""

    def discover(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            return {"row_count": 0, "column_count": 0, "columns": [], "mapping_suggestions": [], "warnings": ["Dataset vacío"]}

        columns = list(rows[0].keys())
        profiles = []
        suggestions: list[MappingSuggestion] = []

        for column in columns:
            values = [row.get(column) for row in rows]
            non_empty = [v for v in values if v not in (None, "")]
            normalized = _normalize_name(str(column))
            completeness = len(non_empty) / len(rows)
            unique_ratio = len({str(v) for v in non_empty}) / len(non_empty) if non_empty else 0
            profiles.append({
                "name": column,
                "normalized_name": normalized,
                "type": _infer_type(values),
                "completeness": round(completeness, 4),
                "unique_ratio": round(unique_ratio, 4),
                "sample": non_empty[:3],
            })

            best: tuple[str, float, str] | None = None
            for target, aliases in ALIASES.items():
                for alias in aliases:
                    alias_norm = _normalize_name(alias)
                    score = 1.0 if normalized == alias_norm else 0.0
                    if score == 0 and (alias_norm in normalized or normalized in alias_norm):
                        score = 0.82
                    if score and (best is None or score > best[1]):
                        best = (target, score, alias)
            if best:
                target, score, alias = best
                suggestions.append(MappingSuggestion(column, target, score, alias, target in REQUIRED_FIELDS))

        mapped_targets = {item.target for item in suggestions if item.confidence >= 0.8}
        warnings: list[str] = []
        missing_required = sorted(REQUIRED_FIELDS - mapped_targets)
        if missing_required:
            warnings.append(f"No se detectaron campos requeridos: {', '.join(missing_required)}")
        low_quality = [p["name"] for p in profiles if p["completeness"] < 0.9]
        if low_quality:
            warnings.append(f"Columnas con cobertura menor al 90%: {', '.join(map(str, low_quality[:10]))}")

        return {
            "row_count": len(rows),
            "column_count": len(columns),
            "columns": profiles,
            "mapping_suggestions": [item.__dict__ for item in suggestions],
            "mapped_target_count": len(mapped_targets),
            "coverage_score": round(len(mapped_targets) / len(ALIASES), 4),
            "warnings": warnings,
        }
