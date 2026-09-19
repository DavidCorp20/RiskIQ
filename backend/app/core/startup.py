from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.data.mongo import MongoRepository


@dataclass
class RuntimeState:
    status: str = "starting"
    mongo: str = "unknown"
    started_at: str | None = None
    checks: dict[str, str] | None = None


runtime_state = RuntimeState(checks={})

CORE_COLLECTIONS = (
    "datasets",
    "portfolio_records",
    "risk_events",
    "risk_actions",
    "decision_history",
    "decision_rules",
)


def initialize_runtime() -> RuntimeState:
    """Best-effort startup checks. Optional integrations never block boot."""
    checks: dict[str, str] = {}
    try:
        repo = MongoRepository("startup_probe")
        repo.ping()
        checks["mongo"] = "ok"
        for collection in CORE_COLLECTIONS:
            try:
                MongoRepository(collection).ensure_indexes()
                checks[f"indexes:{collection}"] = "ok"
            except Exception:
                checks[f"indexes:{collection}"] = "degraded"
        runtime_state.mongo = "ok"
    except Exception as exc:
        checks["mongo"] = f"degraded:{type(exc).__name__}"
        runtime_state.mongo = "degraded"

    optional = {
        "freshservice": settings.freshservice_enabled,
        "market": True,
        "ai": True,
    }
    for name, enabled in optional.items():
        checks[name] = "enabled" if enabled else "disabled"

    runtime_state.status = "ready" if runtime_state.mongo == "ok" else "degraded"
    runtime_state.started_at = datetime.now(timezone.utc).isoformat()
    runtime_state.checks = checks
    return runtime_state


def liveness() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "riskiq-api",
        "runtime": runtime_state.status,
    }


def readiness() -> dict[str, Any]:
    ready = runtime_state.mongo == "ok"
    return {
        "status": "ready" if ready else "degraded",
        "ready": ready,
        "runtime": runtime_state.status,
        "dependencies": runtime_state.checks or {},
    }


def version() -> dict[str, str]:
    return {
        "service": "riskiq-api",
        "version": "0.1.0",
        "contract": "risk-intelligence-v1",
        "environment": settings.app_env,
    }
