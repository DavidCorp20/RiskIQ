from __future__ import annotations

from fastapi import APIRouter

from app.decision.workspace import DecisionWorkspaceService

router = APIRouter(prefix="/v1/workspace", tags=["workspace"])
service = DecisionWorkspaceService()


@router.post("/run")
def run_workspace(payload: dict) -> dict:
    """Run the complete Data-to-Decision workspace contract."""
    return service.run(payload)
