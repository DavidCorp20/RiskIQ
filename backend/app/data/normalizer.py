from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.data.canonical import CANONICAL_FIELDS


@dataclass(frozen=True)
class FieldMapping:
    source: str
    target: str
    confidence: float = 1.0
    required: bool = False


class DataNormalizer:
    """Normalize external columns while preserving the complete source dataset.

    RiskIQ has a canonical financial vocabulary, but unknown/custom columns are
    valuable analytical dimensions (age, employment, vehicle ownership, score,
    geography, etc.) and must survive ingestion unchanged.
    """

    def normalize(self, rows: list[dict[str, Any]], mappings: list[FieldMapping]) -> list[dict[str, Any]]:
        mapping = {item.source: item.target for item in mappings}
        normalized: list[dict[str, Any]] = []
        for row in rows:
            # Preserve every source column first. Canonical mappings then add or
            # override the normalized financial names without destroying custom data.
            output: dict[str, Any] = dict(row)
            for source, target in mapping.items():
                if source in row and target:
                    output[target] = row[source]
            normalized.append(output)
        return normalized

    def validate_required(self, rows: list[dict[str, Any]], required_fields: set[str] | None = None) -> list[str]:
        required = required_fields or {field for field, meta in CANONICAL_FIELDS.items() if meta.get("required")}
        errors: list[str] = []
        for index, row in enumerate(rows):
            missing = sorted(field for field in required if row.get(field) in (None, ""))
            if missing:
                errors.append(f"row {index}: missing {', '.join(missing)}")
        return errors

    def mapping_summary(self, mappings: list[FieldMapping]) -> dict[str, Any]:
        targets = {item.target for item in mappings}
        required = {field for field, meta in CANONICAL_FIELDS.items() if meta.get("required")}
        missing_required = sorted(required - targets)
        return {
            "mapped_fields": len(mappings),
            "canonical_fields": len(CANONICAL_FIELDS),
            "coverage": round(len(targets) / max(1, len(CANONICAL_FIELDS)), 4),
            "missing_required": missing_required,
            "ready_for_normalization": not missing_required,
        }
