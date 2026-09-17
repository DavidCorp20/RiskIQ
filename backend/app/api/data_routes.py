from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.audit.reconciliation import ReconciliationAuditService
from app.config import settings
from app.data.discovery import DataDiscoveryService
from app.data.ingestion import FileIngestionService
from app.data.normalizer import DataNormalizer, FieldMapping
from app.data.persistence import PortfolioPersistenceService
from app.data.portfolio_projection import PortfolioProjectionService
from app.data.quality import DataQualityService
from app.data.reconciliation import preview as reconciliation_preview, snapshot_key

router = APIRouter(prefix="/v1/data", tags=["data"])
ingestion = FileIngestionService()
discovery = DataDiscoveryService()
normalizer = DataNormalizer()
quality = DataQualityService()
projection = PortfolioProjectionService()
persistence = PortfolioPersistenceService()
audit = ReconciliationAuditService()


def _snapshot_key(row: dict) -> str:
    return snapshot_key(row)


def _loan_key(row: dict) -> str:
    return str(row.get("loan_id") or row.get("id") or "").strip()


def _reconciliation_payload(raw: str | None) -> dict:
    if not raw:
        return {}
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("reconciliation must be a JSON object")
    return value


@router.post("/discover")
async def discover_dataset(file: UploadFile = File(...)) -> dict:
    try:
        content = await file.read()
        rows = ingestion.read(file.filename or "upload.csv", content)
        return discovery.discover(rows)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/health")
def database_health() -> dict:
    health = persistence.health()
    return {"database": "mongodb", "environment": settings.app_env, "status": "ok" if all(health.values()) else "degraded", "collections": health}


@router.get("/{dataset_id}/mapping")
def get_dataset_mapping(dataset_id: str) -> dict:
    return {"dataset_id": dataset_id, "mapping": persistence.get_dataset_mapping(dataset_id)}


@router.post("/{dataset_id}/mapping")
def save_dataset_mapping(dataset_id: str, mappings: list[dict]) -> dict:
    try:
        parsed = [FieldMapping(**item) for item in mappings]
        readiness = normalizer.mapping_summary(parsed)
        record_id = persistence.save_dataset_mapping(dataset_id, [item.__dict__ for item in parsed])
        return {"saved": True, "dataset_id": dataset_id, "mapping_id": record_id, "readiness": readiness}
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/project")
def project_dataset(rows: list[dict]) -> dict:
    return projection.project(rows)


def _rebuild_dataset(dataset_id: str, filename: str, quality_result: dict, field_mappings: list[FieldMapping], source_rows: int) -> dict:
    all_history = persistence.portfolio_records.find({"dataset_id": dataset_id}, limit=100000)
    portfolio = projection.project(all_history)
    projection_persisted = persistence.save_projection(portfolio, dataset_id=dataset_id)
    persistence.save_dataset_mapping(dataset_id=dataset_id, mappings=[item.__dict__ for item in field_mappings], source_name=filename)
    total_rows = len(all_history)
    persistence.save_dataset_metadata(
        dataset_id=dataset_id,
        source_name=filename,
        source_rows=total_rows,
        quality_result=quality_result,
        projection_summary={**portfolio["summary"], "snapshot_date": portfolio["summary"].get("snapshot_date")},
    )
    return {"historical_rows": total_rows, "portfolio": portfolio, "projection_persisted": projection_persisted, "source_rows": source_rows}


@router.post("/ingest")
async def ingest_dataset(
    file: UploadFile = File(...),
    mappings: str = Form(...),
    dataset_id: str | None = Form(default=None),
    snapshot_date: str | None = Form(default=None),
    reconciliation: str | None = Form(default=None),
) -> dict:
    """Ingest a snapshot using deterministic historical identity and reconciliation."""
    try:
        content = await file.read()
        filename = file.filename or "upload.csv"
        rows = ingestion.read(filename, content)
        discovery_result = discovery.discover(rows)
        raw_mappings = json.loads(mappings)
        if not isinstance(raw_mappings, list):
            raise ValueError("mappings must be a JSON array")
        field_mappings = [FieldMapping(**item) for item in raw_mappings]
        normalized = normalizer.normalize(rows, field_mappings)
        if snapshot_date:
            for row in normalized:
                if not row.get("snapshot_date"):
                    row["snapshot_date"] = snapshot_date
        if dataset_id and any(not _snapshot_key(row) for row in normalized):
            raise ValueError("An incremental snapshot requires snapshot_date or a mapped snapshot date column.")

        required_fields = {item.target for item in field_mappings if item.required}
        validation_errors = normalizer.validate_required(normalized, required_fields)
        if validation_errors:
            raise ValueError("Required field validation failed: " + "; ".join(validation_errors[:20]))
        try:
            quality_result = quality.assess(normalized, mappings=[item.__dict__ for item in field_mappings])
        except TypeError:
            quality_result = quality.assess(normalized)
        if quality_result["status"] == "blocked":
            raise HTTPException(status_code=422, detail={"message": "Dataset blocked by Data Quality Gate", "persistence_blocked": True, "quality": quality_result})

        resolved_dataset_id = dataset_id or str(uuid4())
        existing_rows = persistence.portfolio_records.find({"dataset_id": resolved_dataset_id}, limit=100000) if dataset_id else []
        reconciliation_report = reconciliation_preview(existing_rows, normalized)
        reconciliation_input = _reconciliation_payload(reconciliation)

        # Existing snapshot collisions become a preview first. This makes enriched
        # reuploads safe and gives the user an explicit decision for financial conflicts.
        has_collisions = reconciliation_report["counts"]["identical"] + reconciliation_report["counts"]["enriched"] + reconciliation_report["counts"]["conflict"] > 0
        if dataset_id and has_collisions and not reconciliation_input:
            return {
                "status": "reconciliation_required",
                "dataset_id": resolved_dataset_id,
                "source_name": filename,
                "source_rows": len(rows),
                "normalized_rows": len(normalized),
                "persistence_blocked": False,
                "quality": quality_result,
                "reconciliation": reconciliation_report,
                "mapping": {"confirmed": True, "mapped_fields": len(field_mappings), "readiness": normalizer.mapping_summary(field_mappings)},
                "discovery": {"coverage_score": discovery_result.get("coverage_score", 0), "warnings": discovery_result.get("warnings", [])},
            }

        # A reconciliation request must resolve every financial conflict explicitly.
        conflicts = {item["key"]: item for item in reconciliation_report["items"] if item["classification"] == "conflict"}
        resolutions = reconciliation_input.get("resolutions") or {}
        missing = sorted(key for key in conflicts if resolutions.get(key) not in {"keep", "force"})
        if missing:
            raise HTTPException(status_code=409, detail={
                "message": "Financial conflicts require a resolution before the snapshot can be committed.",
                "reconciliation": reconciliation_report,
                "unresolved_conflicts": missing,
            })

        existing_by_key = {_snapshot_key(row): row for row in existing_rows if _snapshot_key(row)}
        report_items = reconciliation_report["items"]
        inserted = enriched = identical = updated = conflicts_kept = forced = 0
        for item in report_items:
            key = item["key"]
            incoming = item["incoming"]
            classification = item["classification"]
            loan_id = item["loan_id"]
            snap = item["snapshot_date"]
            existing = existing_by_key.get(key)
            if classification == "inserted":
                persistence.save_normalized_portfolio([incoming], resolved_dataset_id, filename, quality_result)
                audit.record(dataset_id=resolved_dataset_id, operation="inserted", key=key, loan_id=loan_id, snapshot_date=snap, actor=str(reconciliation_input.get("actor") or "user"), incoming=incoming)
                inserted += 1
            elif classification == "identical":
                audit.record(dataset_id=resolved_dataset_id, operation="identical", key=key, loan_id=loan_id, snapshot_date=snap, actor=str(reconciliation_input.get("actor") or "user"), reason="Incoming observation matches the frozen historical observation; ignored.", previous=existing or {}, incoming=incoming)
                identical += 1
            elif classification == "enriched":
                merged = persistence.reconcile_update(existing or {}, incoming, resolved_dataset_id, filename, force=False)
                audit.record(dataset_id=resolved_dataset_id, operation="enriched", key=key, loan_id=loan_id, snapshot_date=snap, actor=str(reconciliation_input.get("actor") or "user"), reason="Incoming file fills previously missing metadata without changing populated values.", previous=existing or {}, incoming=incoming, changed_fields=item.get("added_fields", []))
                audit.record(dataset_id=resolved_dataset_id, operation="updated", key=key, loan_id=loan_id, snapshot_date=snap, actor=str(reconciliation_input.get("actor") or "user"), reason="Applied deterministic metadata merge.", previous=existing or {}, incoming=merged, changed_fields=item.get("added_fields", []))
                enriched += 1
                updated += 1
            elif classification == "conflict":
                resolution = resolutions.get(key)
                audit.record(dataset_id=resolved_dataset_id, operation="conflict", key=key, loan_id=loan_id, snapshot_date=snap, actor=str(reconciliation_input.get("actor") or "user"), reason=str(reconciliation_input.get("reason") or "Financial conflict detected during historical reconciliation."), previous=existing or {}, incoming=incoming, changed_fields=[c["field"] for c in item.get("conflicts", [])])
                if resolution == "keep":
                    conflicts_kept += 1
                    continue
                reason = str((reconciliation_input.get("reasons") or {}).get(key) or reconciliation_input.get("reason") or "Forced historical correction approved by user.")
                merged = persistence.reconcile_update(existing or {}, incoming, resolved_dataset_id, filename, force=True)
                audit.record(dataset_id=resolved_dataset_id, operation="updated", key=key, loan_id=loan_id, snapshot_date=snap, actor=str(reconciliation_input.get("actor") or "user"), reason=reason, previous=existing or {}, incoming=merged, changed_fields=[c["field"] for c in item.get("conflicts", [])])
                forced += 1
                updated += 1

        rebuilt = _rebuild_dataset(resolved_dataset_id, filename, quality_result, field_mappings, len(rows))
        final_counts = {"inserted": inserted, "identical": identical, "enriched": enriched, "conflict": len(conflicts), "conflicts_kept": conflicts_kept, "forced": forced, "updated": updated}
        return {
            "status": "snapshot_reconciled" if dataset_id else "ingested",
            "dataset_id": resolved_dataset_id,
            "source_name": filename,
            "source_rows": len(rows),
            "historical_rows": rebuilt["historical_rows"],
            "normalized_rows": len(normalized),
            "persisted_rows": inserted + updated,
            "persistence_blocked": False,
            "snapshot_date": _snapshot_key(normalized[0]) if normalized else snapshot_date,
            "quality": quality_result,
            "reconciliation": {"counts": final_counts, "committed": True},
            "projection": {**rebuilt["portfolio"]["summary"], "persisted": rebuilt["projection_persisted"]},
            "mapping": {"confirmed": True, "mapped_fields": len(field_mappings), "readiness": normalizer.mapping_summary(field_mappings)},
            "discovery": {"coverage_score": discovery_result.get("coverage_score", 0), "warnings": discovery_result.get("warnings", [])},
        }
    except HTTPException:
        raise
    except (ValueError, json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
