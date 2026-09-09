from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import settings
from app.data.discovery import DataDiscoveryService
from app.data.ingestion import FileIngestionService
from app.data.normalizer import DataNormalizer, FieldMapping
from app.data.persistence import PortfolioPersistenceService
from app.data.quality import DataQualityService

router = APIRouter(prefix="/v1/data", tags=["data"])
ingestion = FileIngestionService()
discovery = DataDiscoveryService()
normalizer = DataNormalizer()
quality = DataQualityService()
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
        "environment": settings.app_env,
        "status": "ok" if all(health.values()) else "degraded",
        "collections": health,
    }


@router.post("/ingest")
async def ingest_dataset(
    file: UploadFile = File(...),
    mappings: str = Form(...),
    dataset_id: str | None = Form(default=None),
) -> dict:
    """Discover, normalize, quality-check and persist a confirmed mapping.

    Persistence is blocked when the deterministic Data Quality Gate reports
    critical issues. Warning-quality datasets may be persisted, but their
    quality status is retained as dataset metadata for downstream review.
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

        quality_result = quality.assess(normalized)
        if quality_result["status"] == "blocked":
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Dataset blocked by Data Quality Gate",
                    "persistence_blocked": True,
                    "quality": quality_result,
                },
            )

        resolved_dataset_id = dataset_id or str(uuid4())
        persisted = persistence.save_normalized_portfolio(
            normalized,
            dataset_id=resolved_dataset_id,
            source_name=filename,
            quality_result=quality_result,
        )

        return {
            "status": "ingested",
            "dataset_id": resolved_dataset_id,
            "source_name": filename,
            "source_rows": len(rows),
            "normalized_rows": len(normalized),
            "persisted_rows": persisted,
            "persistence_blocked": False,
            "quality": quality_result,
            "discovery": {
                "coverage_score": discovery_result.get("coverage_score", 0),
                "warnings": discovery_result.get("warnings", []),
            },
        }
    except HTTPException:
        raise
    except (ValueError, json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
