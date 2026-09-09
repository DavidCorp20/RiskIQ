from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.data.discovery import DataDiscoveryService
from app.data.ingestion import FileIngestionService

router = APIRouter(prefix="/v1/data", tags=["data"])
ingestion = FileIngestionService()
discovery = DataDiscoveryService()


@router.post("/discover")
async def discover_dataset(file: UploadFile = File(...)) -> dict:
    """Read CSV/XLSX data and return profile plus conservative mapping suggestions."""
    try:
        content = await file.read()
        rows = ingestion.read(file.filename or "upload.csv", content)
        return discovery.discover(rows)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
