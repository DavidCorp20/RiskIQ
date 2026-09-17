from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import settings
from app.data.discovery import DataDiscoveryService
from app.data.ingestion import FileIngestionService
from app.data.normalizer import DataNormalizer, FieldMapping
from app.data.persistence import PortfolioPersistenceService
from app.data.portfolio_projection import PortfolioProjectionService
from app.data.quality import DataQualityService

router = APIRouter(prefix="/v1/data", tags=["data"])
ingestion = FileIngestionService()
discovery = DataDiscoveryService()
normalizer = DataNormalizer()
quality = DataQualityService()
projection = PortfolioProjectionService()
persistence = PortfolioPersistenceService()


def _snapshot_key(row: dict) -> str:
    for field in ("snapshot_date", "snapshot_month", "as_of_date"):
        value = row.get(field)
        if value not in (None, ""):
            return str(value)[:10]
    return ""


def _loan_key(row: dict) -> str:
    return str(row.get("loan_id") or row.get("id") or "").strip()


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


@router.post("/ingest")
async def ingest_dataset(
    file: UploadFile = File(...),
    mappings: str = Form(...),
    dataset_id: str | None = Form(default=None),
    snapshot_date: str | None = Form(default=None),
) -> dict:
    """Append a new snapshot while preserving all historical observations and current state."""
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
        existing_keys = {_loan_key(row) + "|" + _snapshot_key(row) for row in existing_rows if _loan_key(row) and _snapshot_key(row)}
        incoming_keys = set()
        for row in normalized:
            loan_id, snap = _loan_key(row), _snapshot_key(row)
            key = loan_id + "|" + snap if loan_id and snap else ""
            if key and (key in existing_keys or key in incoming_keys):
                raise ValueError(f"Duplicate credit observation for loan_id={loan_id} at snapshot={snap}.")
            if key:
                incoming_keys.add(key)

        persisted = persistence.save_normalized_portfolio(normalized, dataset_id=resolved_dataset_id, source_name=filename, quality_result=quality_result)
        all_history = persistence.portfolio_records.find({"dataset_id": resolved_dataset_id}, limit=100000)
        portfolio = projection.project(all_history)
        projection_persisted = persistence.save_projection(portfolio, dataset_id=resolved_dataset_id)
        persistence.save_dataset_mapping(dataset_id=resolved_dataset_id, mappings=[item.__dict__ for item in field_mappings], source_name=filename)
        total_rows = len(all_history)
        persistence.save_dataset_metadata(dataset_id=resolved_dataset_id, source_name=filename, source_rows=total_rows, quality_result=quality_result, projection_summary={**portfolio["summary"], "snapshot_date": portfolio["summary"].get("snapshot_date")})

        return {
            "status": "snapshot_appended" if dataset_id else "ingested",
            "dataset_id": resolved_dataset_id,
            "source_name": filename,
            "source_rows": len(rows),
            "historical_rows": total_rows,
            "normalized_rows": len(normalized),
            "persisted_rows": persisted,
            "persistence_blocked": False,
            "snapshot_date": _snapshot_key(normalized[0]) if normalized else snapshot_date,
            "quality": quality_result,
            "projection": {**portfolio["summary"], "persisted": projection_persisted},
            "mapping": {"confirmed": True, "mapped_fields": len(field_mappings), "readiness": normalizer.mapping_summary(field_mappings)},
            "discovery": {"coverage_score": discovery_result.get("coverage_score", 0), "warnings": discovery_result.get("warnings", [])},
        }
    except HTTPException:
        raise
    except (ValueError, json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
