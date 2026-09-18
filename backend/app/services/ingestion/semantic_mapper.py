from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, asdict
from typing import Any

from rapidfuzz import fuzz, process

from app.core.ai.provider import AIProvider
from app.data.canonical import CANONICAL_FIELDS


ALIASES: dict[str, tuple[str, ...]] = {
    "customer_id": ("customer_id", "cliente", "client_id", "customer_number", "id_cliente", "cod_cliente", "identificacion", "identificación", "cedula", "cédula", "dni"),
    "loan_id": ("loan_id", "credito", "crédito", "credit_id", "loan_number", "contrato", "contrato_id", "prestamo", "préstamo", "id_credito", "id_crédito", "cuenta_credito"),
    "product_id": ("product_id", "producto_id", "id_producto", "product", "producto"),
    "origination_date": ("origination_date", "fecha_desembolso", "fecha desembolso", "desembolso", "start_date", "fecha_otorgamiento", "fecha de otorgamiento", "fecha_apertura"),
    "due_date": ("due_date", "fecha_vencimiento", "fecha vencimiento", "vencimiento", "next_due_date"),
    "snapshot_date": ("snapshot_date", "snapshot_month", "snapshot_month_date", "fecha_corte", "fecha corte", "as_of_date", "corte", "fecha_snapshot", "mes_corte", "mes_snapshot"),
    "scheduled_amount": ("scheduled_amount", "cuota", "cuota_programada", "cuota programada", "installment_amount", "monto_cuota"),
    "paid_amount": ("paid_amount", "pagado", "monto_pagado", "amount_paid", "pago", "pagos"),
    "outstanding_principal": ("outstanding_principal", "saldo", "saldo_capital", "outstanding", "outstanding_balance", "balance", "capital_pendiente", "saldo_pendiente"),
    "status": ("status", "estado", "estatus", "situacion", "situación"),
    "segment": ("segment", "segmento", "categoria", "categoría", "grupo"),
    "dpd": ("dpd", "dias_mora", "días_mora", "dias mora", "días mora", "days_past_due", "mora", "dias_atraso", "días_atraso"),
    "pd": ("pd", "probability_of_default", "probabilidad_default", "probabilidad_de_default"),
    "lgd": ("lgd", "loss_given_default", "perdida_dado_default", "pérdida_dado_default"),
    "ead": ("ead", "exposure_at_default", "exposicion_default", "exposición_default"),
}


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value).strip().lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return re.sub(r"_+", "_", value).strip("_")


def infer_dtype(values: list[Any]) -> str:
    non_null = [v for v in values if v not in (None, "")]
    if not non_null:
        return "empty"
    if all(isinstance(v, bool) for v in non_null):
        return "boolean"
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in non_null):
        return "numeric"

    text = [str(v).strip() for v in non_null]
    date_like = sum(bool(re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}", value)) for value in text)
    if date_like / len(text) >= 0.8:
        return "date"

    unique_ratio = len(set(text)) / len(text)
    return "categorical" if unique_ratio < 0.2 else "text"


@dataclass(frozen=True)
class MappingSuggestion:
    source: str
    target: str | None
    confidence: float
    method: str
    matched_alias: str | None
    required: bool
    reason: str
    dtype: str
    sample: list[Any]


class SemanticColumnMapper:
    """Three-level semantic mapping: exact -> fuzzy -> optional LLM fallback."""

    def __init__(
        self,
        provider: AIProvider | None = None,
        *,
        fuzzy_threshold: float = 85.0,
        llm_threshold: float = 85.0,
    ) -> None:
        self.provider = provider
        self.fuzzy_threshold = fuzzy_threshold
        self.llm_threshold = llm_threshold
        self.alias_to_target = {
            normalize_name(alias): target
            for target, aliases in ALIASES.items()
            for alias in aliases
        }
        self.aliases = list(self.alias_to_target)

    def map_columns(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        columns = list(dict.fromkeys(key for row in rows for key in row))
        suggestions: list[dict[str, Any]] = []

        for column in columns:
            values = [row.get(column) for row in rows]
            suggestion = self._deterministic_or_fuzzy(column, values)
            suggestions.append(asdict(suggestion))

        return {
            "version": "semantic-mapper-v1",
            "canonical_fields": list(CANONICAL_FIELDS),
            "columns": suggestions,
            "unmapped_columns": [s["source"] for s in suggestions if not s["target"]],
            "low_confidence_columns": [
                s["source"] for s in suggestions
                if s["confidence"] < self.llm_threshold
            ],
        }

    async def map_columns_with_ai(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        result = self.map_columns(rows)
        if not self.provider:
            return result

        for item in result["columns"]:
            if item["confidence"] >= self.llm_threshold:
                continue

            values = [row.get(item["source"]) for row in rows]
            context = {
                "column_name": item["source"],
                "normalized_name": normalize_name(item["source"]),
                "dtype": infer_dtype(values),
                "sample_values": [
                    self._safe_sample(v) for v in values if v not in (None, "")
                ][:10],
                "canonical_fields": [
                    {"id": field_id, **metadata}
                    for field_id, metadata in CANONICAL_FIELDS.items()
                ],
            }
            prompt = (
                "Map this source column to at most one RiskIQ canonical field. "
                "Return JSON exactly as {\"target\": string|null, \"confidence\": number, "
                "\"reason\": string}. Confidence must be 0-100. Do not invent a target "
                "when evidence is insufficient."
            )
            try:
                ai_result = await self.provider.generate(prompt, context)
                target = ai_result.get("target")
                confidence = float(ai_result.get("confidence", 0))
                if target not in CANONICAL_FIELDS:
                    target = None
                    confidence = 0
                confidence = max(0.0, min(100.0, confidence))
                if target and confidence >= item["confidence"]:
                    item["target"] = target
                    item["confidence"] = round(confidence, 1)
                    item["method"] = "llm"
                    item["matched_alias"] = None
                    item["required"] = bool(CANONICAL_FIELDS[target].get("required"))
                    item["reason"] = str(ai_result.get("reason") or "Inferencia semántica del proveedor de IA.")
            except (RuntimeError, ValueError, TypeError, KeyError):
                # AI is an enrichment layer. Deterministic mapping remains valid
                # when the provider is unavailable or returns unusable output.
                item["reason"] = f'{item["reason"]} LLM fallback unavailable; deterministic result preserved.'

        result["unmapped_columns"] = [s["source"] for s in result["columns"] if not s["target"]]
        result["low_confidence_columns"] = [
            s["source"] for s in result["columns"] if s["confidence"] < self.llm_threshold
        ]
        return result

    def _deterministic_or_fuzzy(self, column: str, values: list[Any]) -> MappingSuggestion:
        normalized = normalize_name(column)
        dtype = infer_dtype(values)

        if normalized in self.alias_to_target:
            target = self.alias_to_target[normalized]
            return MappingSuggestion(
                column, target, 100.0, "deterministic", normalized, bool(CANONICAL_FIELDS[target].get("required")),
                "Coincidencia exacta con el vocabulario canónico/alias de RiskIQ.",
                dtype, [self._safe_sample(v) for v in values if v not in (None, "")][:5],
            )

        match = process.extractOne(normalized, self.aliases, scorer=fuzz.ratio)
        if match:
            alias, score, _ = match
            if score >= self.fuzzy_threshold:
                target = self.alias_to_target[alias]
                return MappingSuggestion(
                    column, target, round(float(score), 1), "fuzzy", alias,
                    bool(CANONICAL_FIELDS[target].get("required")),
                    f"Coincidencia difusa con el alias '{alias}'.",
                    dtype, [self._safe_sample(v) for v in values if v not in (None, "")][:5],
                )

        return MappingSuggestion(
            column, None, 0.0, "unmapped", None, False,
            "No existe evidencia determinística suficiente para mapear la columna.",
            dtype, [self._safe_sample(v) for v in values if v not in (None, "")][:5],
        )

    @staticmethod
    def _safe_sample(value: Any) -> Any:
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except (AttributeError, ValueError):
                pass
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)


# Compatibility alias for callers that prefer the shorter service name.
SemanticMapper = SemanticColumnMapper
