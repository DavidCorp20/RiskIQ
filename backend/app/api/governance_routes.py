from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from app.decision.rule_repository import DecisionRuleRepository

router = APIRouter(prefix="/v1/decision-builder", tags=["decision-governance"])
rules_repo = DecisionRuleRepository()

ALLOWED = {
    "DRAFT": {"TESTING"},
    "TESTING": {"DRAFT", "APPROVED"},
    "APPROVED": {"DEPLOYED"},
    "DEPLOYED": {"RETIRED"},
    "RETIRED": set(),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _status(rule: dict) -> str:
    return str((rule.get("policy_package") or {}).get("status") or rule.get("status") or "DRAFT").upper()


def _governance(rule: dict) -> dict:
    package = rule.get("policy_package") or {}
    governance = package.get("governance") or {}
    return {"status": _status(rule), **governance}


def _find_versions(policy_id: str, dataset_id: str | None = None) -> list[dict]:
    rows = rules_repo.list(dataset_id=dataset_id, limit=500)
    rows = [r for r in rows if str(r.get("id") or (r.get("policy_package") or {}).get("policy_id")) == policy_id]
    return sorted(rows, key=lambda r: int(r.get("version") or (r.get("policy_package") or {}).get("version") or 0))


@router.get("/policies/{policy_id}/versions")
def policy_versions(policy_id: str, dataset_id: str | None = None) -> dict:
    versions = _find_versions(policy_id, dataset_id)
    return {"policy_id": policy_id, "count": len(versions), "versions": [{
        "id": r.get("id"),
        "name": r.get("name"),
        "version": r.get("version", 1),
        "status": _status(r),
        "governance": _governance(r),
        "dataset_id": r.get("dataset_id"),
        "saved_at": r.get("saved_at"),
    } for r in versions]}


@router.post("/policies/{policy_id}/transition")
def transition_policy(policy_id: str, payload: dict) -> dict:
    dataset_id = payload.get("dataset_id")
    versions = _find_versions(policy_id, dataset_id)
    if not versions:
        raise HTTPException(status_code=404, detail="Policy not found")
    version = int(payload.get("version") or versions[-1].get("version") or 1)
    current = next((r for r in versions if int(r.get("version") or 1) == version), None)
    if current is None:
        raise HTTPException(status_code=404, detail="Policy version not found")
    current_status = _status(current)
    target = str(payload.get("status") or "").upper()
    if target not in ALLOWED.get(current_status, set()):
        raise HTTPException(status_code=409, detail=f"Invalid lifecycle transition: {current_status} -> {target}")
    actor = str(payload.get("actor") or "system")
    now = _now()
    event = {"from": current_status, "to": target, "actor": actor, "at": now, "reason": str(payload.get("reason") or "")}
    governance = deepcopy(_governance(current))
    governance.update({"status": target, "updated_at": now})
    governance.setdefault("created_by", actor)
    governance.setdefault("created_at", (current.get("policy_package") or {}).get("metadata", {}).get("created_at") or current.get("created_at") or now)
    governance.setdefault("approved_by", None)
    governance.setdefault("approved_at", None)
    governance.setdefault("deployed_at", None)
    governance.setdefault("retired_at", None)
    governance.setdefault("audit_trail", [])
    governance["audit_trail"] = [*governance["audit_trail"], event]
    if target == "APPROVED": governance.update({"approved_by": actor, "approved_at": now})
    if target == "DEPLOYED": governance.update({"deployed_by": actor, "deployed_at": now})
    if target == "RETIRED": governance.update({"retired_by": actor, "retired_at": now})
    package = deepcopy(current.get("policy_package") or {})
    package["status"] = target
    package["governance"] = governance
    return {"transitioned": True, "policy_id": policy_id, "version": version, "status": target, "governance": governance, "note": "Governance events are returned as an immutable event stream; the policy package itself is never rewritten by this endpoint."}


@router.post("/policies/{policy_id}/clone")
def clone_policy(policy_id: str, payload: dict) -> dict:
    dataset_id = payload.get("dataset_id")
    versions = _find_versions(policy_id, dataset_id)
    if not versions:
        raise HTTPException(status_code=404, detail="Policy not found")
    source_version = int(payload.get("version") or versions[-1].get("version") or 1)
    source = next((r for r in versions if int(r.get("version") or 1) == source_version), None)
    if source is None:
        raise HTTPException(status_code=404, detail="Source policy version not found")
    next_version = max(int(r.get("version") or 1) for r in versions) + 1
    actor = str(payload.get("actor") or "system")
    now = _now()
    clone = deepcopy(source)
    clone.pop("_id", None)
    clone["version"] = next_version
    clone["saved_at"] = now
    package = deepcopy(clone.get("policy_package") or {})
    package["version"] = next_version
    package["status"] = "DRAFT"
    package["rule_core"] = deepcopy(package.get("rule_core") or clone)
    package["rule_core"]["version"] = next_version
    governance = {
        "status": "DRAFT",
        "created_by": actor,
        "created_at": now,
        "approved_by": None,
        "approved_at": None,
        "deployed_by": None,
        "deployed_at": None,
        "retired_by": None,
        "retired_at": None,
        "parent_version": source_version,
        "change_summary": str(payload.get("change_summary") or "Cloned from previous policy version"),
        "audit_trail": [{"from": source_version, "to": next_version, "action": "CLONE", "actor": actor, "at": now}],
    }
    package["governance"] = governance
    package.setdefault("metadata", {})
    package["metadata"] = {**package["metadata"], "cloned_from_version": source_version, "created_at": now, "saved_at": now}
    clone["policy_package"] = package
    clone["status"] = "DRAFT"
    clone["id"] = policy_id
    clone["name"] = package.get("name") or clone.get("name")
    saved = rules_repo.save(clone, dataset_id or source.get("dataset_id"), source.get("business_id"))
    return {"cloned": True, "policy": saved, "source_version": source_version, "version": next_version, "status": "DRAFT"}
