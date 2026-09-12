from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from app.decision.rule_repository import DecisionRuleRepository
from app.data.mongo import MongoRepository

router = APIRouter(prefix="/v1/decision-builder", tags=["decision-governance"])
rules_repo = DecisionRuleRepository()
events_repo = MongoRepository("policy_governance_events")

ALLOWED = {
    "DRAFT": {"TESTING"},
    "TESTING": {"DRAFT", "APPROVED"},
    "APPROVED": {"DEPLOYED"},
    "DEPLOYED": {"RETIRED"},
    "RETIRED": set(),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _package_status(rule: dict) -> str:
    return str((rule.get("policy_package") or {}).get("status") or rule.get("status") or "DRAFT").upper()


def _version(rule: dict) -> int:
    return int(rule.get("version") or (rule.get("policy_package") or {}).get("version") or 1)


def _effective_status(rule: dict) -> str:
    policy_id = str(rule.get("id") or (rule.get("policy_package") or {}).get("policy_id") or "")
    version = _version(rule)
    events = events_repo.find({"policy_id": policy_id, "version": version}, limit=1000)
    if events:
        events.sort(key=lambda x: str(x.get("at") or x.get("created_at") or ""))
        return str(events[-1].get("to") or _package_status(rule)).upper()
    return _package_status(rule)


def _governance(rule: dict) -> dict:
    package = rule.get("policy_package") or {}
    governance = deepcopy(package.get("governance") or {})
    governance["status"] = _effective_status(rule)
    policy_id = str(rule.get("id") or package.get("policy_id") or "")
    version = _version(rule)
    events = events_repo.find({"policy_id": policy_id, "version": version}, limit=1000)
    events.sort(key=lambda x: str(x.get("at") or x.get("created_at") or ""))
    if events:
        governance["audit_trail"] = [{k: v for k, v in e.items() if k not in {"_id", "policy_id", "version", "created_at"}} for e in events]
        governance["last_transition_at"] = events[-1].get("at")
    return governance


def _find_versions(policy_id: str, dataset_id: str | None = None) -> list[dict]:
    rows = rules_repo.list(dataset_id=dataset_id, limit=500)
    rows = [r for r in rows if str(r.get("id") or (r.get("policy_package") or {}).get("policy_id")) == policy_id]
    return sorted(rows, key=_version)


@router.get("/policies/{policy_id}/versions")
def policy_versions(policy_id: str, dataset_id: str | None = None) -> dict:
    versions = _find_versions(policy_id, dataset_id)
    return {"policy_id": policy_id, "count": len(versions), "versions": [{
        "id": r.get("id"),
        "name": r.get("name"),
        "version": _version(r),
        "status": _effective_status(r),
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
    version = int(payload.get("version") or _version(versions[-1]))
    current = next((r for r in versions if _version(r) == version), None)
    if current is None:
        raise HTTPException(status_code=404, detail="Policy version not found")
    current_status = _effective_status(current)
    target = str(payload.get("status") or "").upper()
    if target not in ALLOWED.get(current_status, set()):
        raise HTTPException(status_code=409, detail=f"Invalid lifecycle transition: {current_status} -> {target}")
    actor = str(payload.get("actor") or "system")
    now = _now()
    event = {
        "policy_id": policy_id,
        "version": version,
        "from": current_status,
        "to": target,
        "actor": actor,
        "at": now,
        "reason": str(payload.get("reason") or ""),
    }
    events_repo.insert(event)
    return {
        "transitioned": True,
        "policy_id": policy_id,
        "version": version,
        "status": target,
        "event": event,
        "governance": {"status": target, "actor": actor, "updated_at": now},
        "immutable": True,
    }


@router.post("/policies/{policy_id}/clone")
def clone_policy(policy_id: str, payload: dict) -> dict:
    dataset_id = payload.get("dataset_id")
    versions = _find_versions(policy_id, dataset_id)
    if not versions:
        raise HTTPException(status_code=404, detail="Policy not found")
    source_version = int(payload.get("version") or _version(versions[-1]))
    source = next((r for r in versions if _version(r) == source_version), None)
    if source is None:
        raise HTTPException(status_code=404, detail="Source policy version not found")
    next_version = max(_version(r) for r in versions) + 1
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
    package["governance"] = {
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
        "audit_trail": [{"action": "CLONE", "from_version": source_version, "to_version": next_version, "actor": actor, "at": now}],
    }
    package.setdefault("metadata", {})
    package["metadata"] = {**package["metadata"], "cloned_from_version": source_version, "created_at": now, "saved_at": now}
    clone["policy_package"] = package
    clone["status"] = "DRAFT"
    clone["id"] = policy_id
    clone["name"] = package.get("name") or clone.get("name")
    saved = rules_repo.save(clone, dataset_id or source.get("dataset_id"), source.get("business_id"))
    events_repo.insert({"policy_id": policy_id, "version": next_version, "from": source_version, "to": "DRAFT", "action": "CLONE", "actor": actor, "at": now})
    return {"cloned": True, "policy": saved, "source_version": source_version, "version": next_version, "status": "DRAFT", "immutable_source": True}
