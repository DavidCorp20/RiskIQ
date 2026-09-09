from __future__ import annotations

from fastapi import APIRouter

from app.analytics.snapshot_engine import SnapshotEngine
from app.data.persistence import PortfolioPersistenceService

router = APIRouter(prefix="/v1/portfolio", tags=["portfolio-history"])
engine = SnapshotEngine()
persistence = PortfolioPersistenceService()


@router.post("/snapshot")
def build_snapshot(payload: dict) -> dict:
    """Build and persist one point-in-time portfolio snapshot."""
    snapshot = engine.build(
        loans=payload.get("loans", []),
        installments=payload.get("installments", []),
        snapshot_date=payload["snapshot_date"],
        business_id=payload.get("business_id"),
    )
    snapshot_id = persistence.snapshots.insert(snapshot)
    return {"status": "created", "snapshot_id": snapshot_id, "snapshot": snapshot}


@router.get("/snapshots")
def list_snapshots(business_id: str | None = None, limit: int = 100) -> dict:
    """Return stored portfolio snapshots ordered by persistence order."""
    filters = {"business_id": business_id} if business_id else {}
    snapshots = persistence.snapshots.find(filters, limit=max(1, min(limit, 500)))
    return {"count": len(snapshots), "snapshots": snapshots}
