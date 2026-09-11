from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException

from app.ai.copilot import RiskCopilotService
from app.analytics.decision_engine import DecisionEngineService
from app.analytics.npl import NPLAnalyticsService
from app.analytics.portfolio_intelligence import PortfolioIntelligenceService
from app.analytics.risk_analytics import RiskAnalyticsService
from app.analytics.snapshot_engine import SnapshotEngine
from app.data.persistence import PortfolioPersistenceService

router = APIRouter(prefix="/v1/ai", tags=["ai"])
service = RiskCopilotService()
persistence = PortfolioPersistenceService()
intelligence = PortfolioIntelligenceService()
risk_analytics = RiskAnalyticsService()
decision_engine = DecisionEngineService()
npl = NPLAnalyticsService()
snapshot_engine = SnapshotEngine()


def _require_dataset(dataset_id: str) -> dict[str, Any]:
    rows = persistence.datasets.find({"dataset_id": dataset_id}, limit=1)
    if not rows:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return rows[0]


def _resolve_dataset_id(payload: dict) -> str:
    """Resolve dataset lineage, with a safe legacy-client fallback."""
    explicit = str(payload.get("dataset_id") or "").strip()
    if explicit:
        return explicit

    candidates = persistence.datasets.find({}, limit=100)
    if not candidates:
        return ""

    latest = max(candidates, key=lambda row: str(row.get("created_at") or ""))
    return str(latest.get("dataset_id") or "").strip()


def _build_grounded_context(dataset_id: str) -> dict[str, Any]:
    """Rebuild deterministic evidence when the client omits or sends incomplete facts."""
    records = persistence.portfolio_records.find({"dataset_id": dataset_id}, limit=100000)
    if not records:
        raise HTTPException(status_code=422, detail="Dataset has no portfolio records for Copilot grounding")

    analysis = intelligence.analyze(records)
    risk = risk_analytics.analyze(records)
    npl_analysis = npl.analyze(records)
    decisions = decision_engine.build(risk, npl_analysis)

    loans = persistence.loans.find({"dataset_id": dataset_id}, limit=100000)
    installments = persistence.installments.find({"dataset_id": dataset_id}, limit=100000)
    snapshot_date = date.today().isoformat()
    snapshot = snapshot_engine.build(
        loans=loans,
        installments=installments,
        snapshot_date=snapshot_date,
        business_id=dataset_id,
    ) if loans else {}

    facts: dict[str, Any] = {}
    deterministic = risk if isinstance(risk, dict) else {}
    par = deterministic.get("par") or {}
    for key in ("par7", "par30", "par60", "par90"):
        value = par.get(key) or {}
        if isinstance(value, dict) and "ratio" in value:
            facts[key] = {"id": key, "label": key.upper(), "value": value.get("ratio"), "unit": ""}

    exposure = deterministic.get("exposure", snapshot.get("outstanding_balance"))
    if exposure is not None:
        facts["exposure"] = {"id": "exposure", "label": "Exposure", "value": exposure, "unit": ""}

    loan_count = deterministic.get("loan_count", snapshot.get("active_loans"))
    if loan_count is not None:
        facts["loan_count"] = {"id": "loan_count", "label": "Loans", "value": loan_count, "unit": ""}

    drivers = deterministic.get("drivers") or analysis.get("drivers") or []
    priority_cards = decisions.get("priority_cards") if isinstance(decisions, dict) else []
    if not isinstance(priority_cards, list):
        priority_cards = []

    alerts = priority_cards or deterministic.get("alerts") or []
    status = (decisions.get("status") if isinstance(decisions, dict) else None) or "observed"

    return {
        "dataset_id": dataset_id,
        "facts": facts,
        "alerts": alerts,
        "summary": {"status": status},
        "drivers": drivers,
        "decisions": priority_cards,
    }


@router.post("/copilot")
def copilot(payload: dict) -> dict:
    """Answer using deterministic evidence tied to one persisted dataset."""
    dataset_id = _resolve_dataset_id(payload)
    if not dataset_id:
        raise HTTPException(status_code=400, detail="dataset_id is required for dataset-bound Copilot")

    _require_dataset(dataset_id)
    supplied = payload.get("risk_facts")
    risk_facts = supplied if isinstance(supplied, dict) else {}

    supplied_lineage = str(risk_facts.get("dataset_id") or "").strip()
    if supplied_lineage and supplied_lineage != dataset_id:
        raise HTTPException(status_code=409, detail="risk_facts dataset_id does not match requested dataset")

    drivers = payload.get("drivers") if isinstance(payload.get("drivers"), list) else []
    decisions = payload.get("decisions") if isinstance(payload.get("decisions"), list) else []

    # The frontend may send decisions/drivers while still omitting the actual
    # calculated facts. Facts are the source of truth, so rebuild whenever they
    # are absent instead of allowing auxiliary payload fields to suppress grounding.
    has_facts = isinstance(risk_facts.get("facts"), dict) and bool(risk_facts.get("facts"))
    if not has_facts:
        risk_facts = _build_grounded_context(dataset_id)
        drivers = risk_facts.pop("drivers", [])
        decisions = risk_facts.pop("decisions", [])

    answer = service.answer(
        question=str(payload.get("question", "")),
        risk_facts=risk_facts,
        drivers=drivers,
        decisions=decisions,
    )
    answer["dataset_id"] = dataset_id
    answer["grounding"] = {
        "dataset_bound": True,
        "evidence_rebuilt_server_side": bool(not has_facts),
        "customer_actions_executed": False,
        "causality_inferred": False,
    }
    return answer
