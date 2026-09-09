from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.data.discovery import DataDiscoveryService
from app.data.ingestion import FileIngestionService
from app.data.normalizer import DataNormalizer, FieldMapping
from app.data.persistence import PortfolioPersistenceService

router = APIRouter(prefix="/v1/data", tags=["data"])
ingestion = FileIngestionService()
discovery = DataDiscoveryService()
normalizer = DataNormalizer()
persistence = PortfolioPersistenceService()


@router.post("/discover")
async def discover_dataset(file: UploadFile = File(...)) -> dict:
    """Read CSV/XLSX data and return profile plus conservative mapping suggestions."""
    try:
        content = await file.read()
        rows = ingestion.read(file.filename or "upload.csv", content)
        return discovery.discover(rows)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/health")
def database_health() -> dict:
    """Check connectivity to the configured MongoDB database."""
    health = persistence.health()
    return {
        "database": "mongodb",
        "environment": __import__("app.config", fromlist=["settings"]).settings.app_env,
        "status": "ok" if all(health.values()) else "degraded",
        "collections": health,
    }


@router.post("/ingest")
async def ingest_dataset(
    file: UploadFile = File(...),
    mappings: str = Form(...),
    dataset_id: str | None = Form(default=None),
) -> dict:
    """Discover, normalize and persist a confirmed mapping into MongoDB.

    `mappings` is a JSON array of objects with `source`, `target` and optional
    `required`. The endpoint deliberately requires explicit mappings so RiskIQ
    never silently converts an uncertain source column into a canonical field.
    """
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
        required_fields = {item.target for item in field_mappings if item.required}
        validation_errors = normalizer.validate_required(normalized, required_fields)
        if validation_errors:
            raise ValueError("Required field validation failed: " + "; ".join(validation_errors[:20]))

        resolved_dataset_id = dataset_id or str(uuid4())
        persisted = persistence.save_normalized_portfolio(
            normalized,
            dataset_id=resolved_dataset_id,
            source_name=filename,
        )

        return {
            "status": "ingested",
            "dataset_id": resolved_dataset_id,
            "source_name": filename,
            "source_rows": len(rows),
            "normalized_rows": len(normalized),
            "persisted_rows": persisted,
            "discovery": {
                "coverage_score": discovery_result.get("coverage_score", 0),
                "warnings": discovery_result.get("warnings", []),
            },
        }
    except (ValueError, json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
