from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FieldMapping:
    source: str
    target: str
    required: bool = False


CANONICAL_FIELDS = {
    "customer_id",
    "loan_id",
    "product_id",
    "origination_date",
    "due_date",
    "scheduled_amount",
    "paid_amount",
    "outstanding_principal",
    "status",
    "segment",
}


class DataNormalizer:
    """Normalize external column names into RiskIQ canonical fields."""

    def normalize(self, rows: list[dict[str, Any]], mappings: list[FieldMapping]) -> list[dict[str, Any]]:
        mapping = {item.source: item.target for item in mappings}
        unknown_targets = set(mapping.values()) - CANONICAL_FIELDS
        if unknown_targets:
            raise ValueError(f"Unknown canonical fields: {sorted(unknown_targets)}")

        normalized = []
        for row in rows:
            normalized.append({target: row[source] for source, target in mapping.items() if source in row})
        return normalized

    def validate_required(self, rows: list[dict[str, Any]], required_fields: set[str]) -> list[str]:
        errors: list[str] = []
        for index, row in enumerate(rows):
            missing = sorted(field for field in required_fields if row.get(field) in (None, ""))
            if missing:
                errors.append(f"row {index}: missing {', '.join(missing)}")
        return errors
