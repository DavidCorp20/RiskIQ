from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any


# These fields change the financial/risk meaning of a point-in-time observation.
CRITICAL_FIELDS = {
    "outstanding_principal",
    "dpd",
    "status",
    "paid_amount",
    "scheduled_amount",
    "installment_amount",
    "principal",
}

IDENTITY_FIELDS = {"loan_id", "snapshot_date", "snapshot_month", "as_of_date"}


def _empty(value: Any) -> bool:
    return value is None or value == ""


def _normalize(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()[:10] if isinstance(value, datetime) or isinstance(value, date) else value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, str):
        return value.strip()
    return value


def snapshot_key(row: dict[str, Any]) -> str:
    loan_id = str(row.get("loan_id") or row.get("id") or "").strip()
    snapshot = ""
    for field in ("snapshot_date", "snapshot_month", "as_of_date"):
        value = row.get(field)
        if not _empty(value):
            snapshot = str(_normalize(value))[:10]
            break
    return f"{loan_id}|{snapshot}" if loan_id and snapshot else ""


def _display(value: Any) -> Any:
    if _empty(value):
        return None
    return value


@dataclass(frozen=True)
class ReconciliationItem:
    key: str
    loan_id: str
    snapshot_date: str
    classification: str
    existing: dict[str, Any]
    incoming: dict[str, Any]
    added_fields: list[str]
    changed_fields: list[str]
    conflicts: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "loan_id": self.loan_id,
            "snapshot_date": self.snapshot_date,
            "classification": self.classification,
            "added_fields": self.added_fields,
            "changed_fields": self.changed_fields,
            "conflicts": self.conflicts,
            "existing": self.existing,
            "incoming": self.incoming,
        }


def classify(existing: dict[str, Any], incoming: dict[str, Any]) -> ReconciliationItem:
    key = snapshot_key(incoming) or snapshot_key(existing)
    loan_id = str(incoming.get("loan_id") or existing.get("loan_id") or "").strip()
    snapshot = key.split("|", 1)[1] if "|" in key else ""
    fields = sorted((set(existing) | set(incoming)) - IDENTITY_FIELDS - {"dataset_id", "source_name", "created_at", "_id"})
    added: list[str] = []
    changed: list[str] = []
    conflicts: list[dict[str, Any]] = []

    for field in fields:
        old = _normalize(existing.get(field))
        new = _normalize(incoming.get(field))
        if _empty(old) and not _empty(new):
            added.append(field)
            continue
        if _empty(new) or old == new:
            continue
        changed.append(field)
        conflicts.append({
            "field": field,
            "critical": field in CRITICAL_FIELDS,
            "previous": _display(old),
            "incoming": _display(new),
        })

    if not changed and not added:
        classification = "identical"
    elif not conflicts:
        classification = "enriched"
    else:
        classification = "conflict"

    return ReconciliationItem(key, loan_id, snapshot, classification, existing, incoming, added, changed, conflicts)


def preview(existing_rows: list[dict[str, Any]], incoming_rows: list[dict[str, Any]]) -> dict[str, Any]:
    existing_by_key = {snapshot_key(row): row for row in existing_rows if snapshot_key(row)}
    seen: set[str] = set()
    items: list[ReconciliationItem] = []
    duplicate_in_file: list[dict[str, Any]] = []

    for row in incoming_rows:
        key = snapshot_key(row)
        if not key:
            continue
        if key in seen:
            duplicate_in_file.append({"key": key, "loan_id": str(row.get("loan_id") or ""), "snapshot_date": key.split("|", 1)[1]})
            continue
        seen.add(key)
        existing = existing_by_key.get(key)
        if existing is None:
            items.append(ReconciliationItem(key, key.split("|", 1)[0], key.split("|", 1)[1], "inserted", {}, row, [], [], []))
        else:
            items.append(classify(existing, row))

    counts = {name: sum(item.classification == name for item in items) for name in ("inserted", "identical", "enriched", "conflict")}
    return {
        "required": any(item.classification == "conflict" for item in items),
        "items": [item.to_dict() for item in items],
        "duplicate_in_file": duplicate_in_file,
        "counts": counts,
        "total": len(items),
    }


def merge_enriched(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """Fill previously missing attributes without changing a populated value."""
    merged = dict(existing)
    for field, value in incoming.items():
        if field in IDENTITY_FIELDS or field in {"dataset_id", "source_name", "created_at", "_id"}:
            continue
        if _empty(merged.get(field)) and not _empty(value):
            merged[field] = value
    return merged
