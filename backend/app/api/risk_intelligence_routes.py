from fastapi import APIRouter, HTTPException
from app.services.risk_intelligence_provider import RiskIntelligenceProvider

router = APIRouter(prefix="/v1/risk-intelligence", tags=["risk-intelligence"])
provider = RiskIntelligenceProvider()


@router.get("/{dataset_id}")
async def get_risk_intelligence(dataset_id: str, snapshot_id: str | None = None):
    try:
        return await provider.build(dataset_id, snapshot_id=snapshot_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
