from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.ai.provider import get_ai_provider
from app.data.ingestion import FileIngestionService
from app.services.ingestion.data_quality import DataQualityEngine
from app.services.ingestion.semantic_mapper import SemanticColumnMapper


router = APIRouter(prefix="/v1/data", tags=["smart-ingestion"])

ingestion = FileIngestionService()
quality_engine = DataQualityEngine()

MAX_FILE_BYTES = 25 * 1024 * 1024
MAPPING_ACCEPTANCE_THRESHOLD = 85.0


def _accepted_mappings(mapping_result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "source": item["source"],
            "target": item["target"],
            "confidence": item["confidence"],
            "required": item["required"],
            "method": item["method"],
        }
        for item in mapping_result.get("columns", [])
        if item.get("target") and float(item.get("confidence", 0)) >= MAPPING_ACCEPTANCE_THRESHOLD
    ]


@router.post("/smart-ingest")
async def smart_ingest(file: UploadFile = File(...)) -> dict[str, Any]:
    """Profile, semantically map and deterministically quality-gate a CSV/XLSX upload.

    This endpoint is intentionally non-persistent: it prepares an evidence package
    for the existing /discover + /ingest flow and does not alter existing datasets.
    """
    filename = file.filename or "upload.csv"
    extension = Path(filename).suffix.lower()
    if extension not in FileIngestionService.SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. RiskIQ accepts CSV and XLSX files.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded file exceeds the 25 MB Smart Ingestion limit.")

    try:
        rows = ingestion.read(filename, content)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not rows:
        raise HTTPException(status_code=422, detail="Dataset contains no data rows.")

    provider_name = "gemini"
    try:
        provider = get_ai_provider()
        provider_name = provider.__class__.__name__.replace("Provider", "").lower()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    mapper = SemanticColumnMapper(
        provider=provider,
        fuzzy_threshold=MAPPING_ACCEPTANCE_THRESHOLD,
        llm_threshold=MAPPING_ACCEPTANCE_THRESHOLD,
    )
    mapping_result = await mapper.map_columns_with_ai(rows)
    accepted = _accepted_mappings(mapping_result)

    quality_result = quality_engine.assess(rows, mappings=accepted)

    deterministic_count = sum(
        item.get("method") == "deterministic"
        for item in mapping_result["columns"]
        if item.get("target")
    )
    fuzzy_count = sum(
        item.get("method") == "fuzzy"
        for item in mapping_result["columns"]
        if item.get("target")
    )
    llm_count = sum(
        item.get("method") == "llm"
        for item in mapping_result["columns"]
        if item.get("target")
    )

    readiness = quality_result["analysis_readiness"]
    ready_models = [name for name, state in readiness.items() if state.get("ready")]
    blocked_models = [name for name, state in readiness.items() if not state.get("ready")]

    return {
        "contract_version": "smart-ingest-v1",
        "status": "ready_for_analysis" if quality_result["status"] != "blocked" and not blocked_models else "review_required",
        "persistence": {
            "persisted": False,
            "message": "Smart Ingestion is a pre-ingestion gate. Existing /discover and /ingest endpoints remain unchanged.",
        },
        "source": {
            "filename": filename,
            "extension": extension,
            "bytes": len(content),
            "row_count": len(rows),
            "column_count": len({key for row in rows for key in row}),
        },
        "profiling": {
            "columns": mapping_result["columns"],
            "mapping_counts": {
                "deterministic": deterministic_count,
                "fuzzy": fuzzy_count,
                "llm": llm_count,
                "unmapped": len(mapping_result["unmapped_columns"]),
            },
        },
        "mapping": {
            "acceptance_threshold": MAPPING_ACCEPTANCE_THRESHOLD,
            "accepted": accepted,
            "unmapped_columns": mapping_result["unmapped_columns"],
            "low_confidence_columns": mapping_result["low_confidence_columns"],
        },
        "ai": {
            "provider": provider_name,
            "principle": "AI infers semantic equivalence; deterministic engines calculate quality and risk.",
        },
        "quality": quality_result,
        "risk_model_readiness": {
            "ready_models": ready_models,
            "blocked_or_incomplete_models": blocked_models,
            "next_step": "Proceed to the existing /api/v1/data/ingest endpoint after analyst confirmation of the mapping." if not blocked_models else "Review mapping and quality findings before ingestion.",
        },
    }
