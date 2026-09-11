from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.ai.copilot import RiskCopilotService
from app.data.persistence import PortfolioPersistenceService

router = APIRouter(prefix="/v1/ai", tags=["ai"])
service = RiskCopilotService()
persistence = PortfolioPersistenceService()


def _require_dataset(dataset_id: str) -> dict:
    rows = persistence.datasets.find({"dataset_id": dataset_id}, limit=1)
    if not rows:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return rows[0]


def _resolve_dataset_id(payload: dict) -> str:
    """Resolve an explicit dataset first; only infer when exactly one dataset exists."""
    explicit = str(payload.get("dataset_id") or "").strip()
    if explicit:
        return explicit

    candidates = persistence.datasets.find({}, limit=2)
    if len(candidates) == 1:
        return str(candidates[0].get("dataset_id") or "").strip()

    return ""


@router.post("/copilot")
def copilot(payload: dict) -> dict:
    """Answer using deterministic evidence explicitly tied to one persisted dataset."""
    dataset_id = _resolve_dataset_id(payload)
    if not dataset_id:
        raise HTTPException(status_code=400, detail="dataset_id is required for dataset-bound Copilot")

    _require_dataset(dataset_id)
    risk_facts = payload.get("risk_facts", {})
    if not isinstance(risk_facts, dict):
        raise HTTPException(status_code=400, detail="risk_facts must be an object")

    supplied_lineage = str(risk_facts.get("dataset_id") or "").strip()
    if supplied_lineage and supplied_lineage != dataset_id:
        raise HTTPException(status_code=409, detail="risk_facts dataset_id does not match requested dataset")

    answer = service.answer(
        question=str(payload.get("question", "")),
        risk_facts=risk_facts,
        drivers=payload.get("drivers", []),
        decisions=payload.get("decisions", []),
    )
    answer["dataset_id"] = dataset_id
    answer["grounding"] = {
        "dataset_bound": True,
        "customer_actions_executed": False,
        "causality_inferred": False,
    }
    return answer
