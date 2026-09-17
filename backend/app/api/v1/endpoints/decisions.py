from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.analytics.decision_engine import RiskDecisionEngine
from app.repositories.risk_repository import RiskAnalysisRepository
from app.schemas.decision import DecisionAssessmentResponse, DecisionEvaluationRequest

router = APIRouter(prefix="/v1/risk/decisions", tags=["risk-decisions"])
engine = RiskDecisionEngine()


@router.post(
    "/evaluate",
    response_model=DecisionAssessmentResponse,
    status_code=status.HTTP_200_OK,
)
def evaluate_decision(request: DecisionEvaluationRequest) -> DecisionAssessmentResponse:
    """Evaluate deterministic credit policies from persisted or direct analytics."""
    payload = request.payload
    dataset_id = request.dataset_id
    result_id = request.result_id

    if result_id:
        repository = RiskAnalysisRepository()
        analysis = repository.get_analysis_by_id(result_id)
        if analysis is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis result not found",
            )
        payload = analysis.get("payload") or {}
        dataset_id = str(analysis.get("dataset_id") or dataset_id or "")

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either result_id or payload is required",
        )
    if not dataset_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="dataset_id is required when evaluating a direct payload",
        )

    result = engine.evaluate(
        payload,
        dataset_id=dataset_id,
        result_id=result_id,
    )
    return DecisionAssessmentResponse(**result)
