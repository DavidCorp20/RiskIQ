from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings
from app.data.mongo import MongoRepository

logger = logging.getLogger(__name__)


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
CRITICAL_POLICY_STATUSES = {
    value.strip().upper()
    for value in settings.freshservice_critical_policy_statuses.split(",")
    if value.strip()
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _retry_after(response: httpx.Response) -> float:
    value = response.headers.get("Retry-After")
    try:
        return min(max(float(value), 0.0), settings.freshservice_max_retry_delay_seconds)
    except (TypeError, ValueError):
        return 0.0


class FreshserviceClient:
    """Async Freshservice v2 client with connection reuse and bounded retries."""

    def __init__(self) -> None:
        self.base_url = settings.freshservice_base_url.rstrip("/")
        self.api_key = settings.freshservice_api_key
        self.timeout = httpx.Timeout(settings.freshservice_timeout_seconds)
        self.limits = httpx.Limits(
            max_connections=settings.freshservice_max_connections,
            max_keepalive_connections=settings.freshservice_max_keepalive_connections,
        )

    @property
    def enabled(self) -> bool:
        return bool(settings.freshservice_enabled and self.base_url and self.api_key)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            auth=httpx.BasicAuth(self.api_key, "X"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "RiskIQ-Freshservice/1.0",
            },
            timeout=self.timeout,
            limits=self.limits,
            http2=True,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Freshservice integration is not configured")

        last_error: Exception | None = None

        async with self._client() as client:
            for attempt in range(settings.freshservice_max_retries + 1):
                try:
                    response = await client.request(method, path, json=json_payload)

                    if response.status_code not in RETRYABLE_STATUS_CODES:
                        response.raise_for_status()
                        if not response.content:
                            return {}
                        return response.json()

                    if attempt >= settings.freshservice_max_retries:
                        response.raise_for_status()

                    delay = _retry_after(response)
                    if delay <= 0:
                        delay = settings.freshservice_retry_backoff_seconds * (2**attempt)

                    await asyncio.sleep(
                        min(delay, settings.freshservice_max_retry_delay_seconds)
                    )

                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    last_error = exc
                    if attempt >= settings.freshservice_max_retries:
                        raise
                    delay = min(
                        settings.freshservice_retry_backoff_seconds * (2**attempt),
                        settings.freshservice_max_retry_delay_seconds,
                    )
                    await asyncio.sleep(delay)

        if last_error:
            raise last_error
        raise RuntimeError("Freshservice request failed without a response")

    async def create_ticket(self, ticket: dict[str, Any]) -> dict[str, Any]:
        result = await self._request("POST", "/api/v2/tickets", json_payload=ticket)
        return dict(result.get("ticket") or result)

    async def update_ticket(self, ticket_id: int | str, ticket: dict[str, Any]) -> dict[str, Any]:
        result = await self._request(
            "PUT",
            f"/api/v2/tickets/{ticket_id}",
            json_payload=ticket,
        )
        return dict(result.get("ticket") or result)


class ComplianceAutomationService:
    """Durable RiskIQ -> Freshservice compliance synchronization.

    RiskIQ writes an append-only outbox record first. Freshservice synchronization
    happens asynchronously, so risk/decision requests are not blocked by the
    external ITSM provider. Failed records remain pending for a later retry.
    """

    def __init__(self) -> None:
        self.outbox = MongoRepository("compliance_outbox")
        self.sync = MongoRepository("freshservice_compliance_sync")
        self.client = FreshserviceClient()
        self._indexes_ready = False

    def _ensure_indexes(self) -> None:
        if self._indexes_ready:
            return
        self.outbox.ensure_indexes()
        self.outbox._collection.create_index([("event_key", 1)], unique=True)
        self.outbox._collection.create_index([("status", 1), ("created_at", 1)])
        self.sync.ensure_indexes()
        self.sync._collection.create_index([("sync_key", 1)], unique=True)
        self.sync._collection.create_index([("freshservice_ticket_id", 1)])
        self._indexes_ready = True

    def enqueue(
        self,
        *,
        event_type: str,
        event: dict[str, Any],
        critical: bool = True,
    ) -> dict[str, Any]:
        self._ensure_indexes()

        event_payload = {
            "event_type": event_type,
            "critical": critical,
            "event": event,
        }
        event_key = f"{event_type}:{_stable_hash(event)}"

        existing = self.outbox.find({"event_key": event_key}, limit=1)
        if existing:
            return existing[0]

        document = {
            "event_key": event_key,
            **event_payload,
            "status": "pending",
            "attempts": 0,
            "last_error": None,
            "created_at": _now(),
            "updated_at": _now(),
        }
        self.outbox.insert(document)
        return document

    async def process_pending(self, limit: int = 20) -> dict[str, int]:
        self._ensure_indexes()
        if not self.client.enabled:
            return {"processed": 0, "succeeded": 0, "failed": 0, "disabled": 0}

        pending = self.outbox.find({"status": {"$in": ["pending", "retry"]}}, limit=limit)
        succeeded = 0
        failed = 0

        for item in pending:
            try:
                result = await self._process_event(item)
                external_id = result.get("freshservice_ticket_id") if isinstance(result, dict) else None
                self.outbox.update(
                    {"event_key": item["event_key"]},
                    {
                        "$set": {
                            "status": "delivered",
                            "external_id": external_id,
                            "last_error": None,
                            "updated_at": _now(),
                        },
                        "$inc": {"attempts": 1},
                    },
                )
                succeeded += 1
            except Exception as exc:
                logger.exception("RiskIQ Freshservice sync failed")
                self.outbox.update(
                    {"event_key": item["event_key"]},
                    {
                        "$set": {
                            "status": "retry",
                            "last_error": str(exc)[:1000],
                            "updated_at": _now(),
                        },
                        "$inc": {"attempts": 1},
                    },
                )
                failed += 1

        return {
            "processed": succeeded + failed,
            "succeeded": succeeded,
            "failed": failed,
            "disabled": 0,
        }

    async def _process_event(self, item: dict[str, Any]) -> dict[str, Any]:
        event_type = str(item["event_type"])
        event = dict(item.get("event") or {})

        if event_type == "policy_transition":
            return await self._sync_policy_transition(event)
        elif event_type == "decision_execution":
            return await self._sync_decision_execution(event)
        elif event_type == "decision_review_transition":
            return await self._sync_decision_review_transition(event)
        else:
            raise ValueError(f"Unsupported compliance event: {event_type}")

    async def _sync_policy_transition(self, event: dict[str, Any]) -> dict[str, Any]:
        policy_id = str(event.get("policy_id") or "")
        version = int(event.get("version") or 1)
        target_status = str(event.get("to") or "").upper()
        if not policy_id:
            raise ValueError("policy_id is required")

        sync_key = f"policy:{policy_id}:v{version}"
        title = f"RiskIQ Compliance | Policy {policy_id} v{version}"
        description = self._policy_description(event)

        return await self._upsert_ticket(
            sync_key=sync_key,
            subject=title,
            description=description,
            priority=4 if target_status in CRITICAL_POLICY_STATUSES else 3,
            tags=["riskiq", "riskiq-compliance", "risk-policy"],
            custom_fields={
                "riskiq_event_type": "policy_transition",
                "riskiq_policy_id": policy_id,
                "riskiq_policy_version": version,
                "riskiq_policy_status": target_status,
            },
        )

    async def _sync_decision_review_transition(self, event: dict[str, Any]) -> dict[str, Any]:
        decision_id = str(event.get("decision_id") or "")
        if not decision_id:
            raise ValueError("decision_id is required")
        status = str(event.get("review_state") or event.get("status") or "").upper()
        action_level = str(event.get("action_level") or "").lower()
        title = f"RiskIQ Compliance | Decision Review {decision_id} | {status}"
        description = self._decision_review_description(event)
        return await self._upsert_ticket(
            sync_key=f"decision-review:{decision_id}:{status}",
            subject=title,
            description=description,
            priority=4 if action_level in {"medium", "high"} else 3,
            tags=["riskiq", "riskiq-compliance", "decision-review"],
            custom_fields={
                "riskiq_event_type": "decision_review_transition",
                "riskiq_decision_id": decision_id,
                "riskiq_review_state": status,
                "riskiq_evidence_hash": event.get("evidence_hash"),
                "riskiq_policy_id": event.get("policy_id"),
                "riskiq_policy_version": event.get("policy_version"),
            },
        )

    async def _sync_decision_execution(self, event: dict[str, Any]) -> dict[str, Any]:
        decision_id = str(event.get("decision_id") or "")
        if not decision_id:
            raise ValueError("decision_id is required")

        status = str(event.get("status") or "executed").upper()
        title = f"RiskIQ Compliance | Decision {decision_id}"
        description = self._decision_description(event)

        return await self._upsert_ticket(
            sync_key=f"decision:{decision_id}",
            subject=title,
            description=description,
            priority=4 if event.get("critical", True) else 3,
            tags=["riskiq", "riskiq-compliance", "risk-decision"],
            custom_fields={
                "riskiq_event_type": "decision_execution",
                "riskiq_decision_id": decision_id,
                "riskiq_decision_status": status,
                "riskiq_policy_id": event.get("policy_id"),
                "riskiq_policy_version": event.get("policy_version"),
            },
        )

    async def _upsert_ticket(
        self,
        *,
        sync_key: str,
        subject: str,
        description: str,
        priority: int,
        tags: list[str],
        custom_fields: dict[str, Any],
    ) -> dict[str, Any]:
        self._ensure_indexes()
        current = self.sync.find({"sync_key": sync_key}, limit=1)
        ticket_payload = {
            "subject": subject,
            "description": description,
            "priority": priority,
            "status": 2,
            "source": 2,
            "tags": tags,
            "custom_fields": {
                key: value
                for key, value in custom_fields.items()
                if value is not None
            },
        }
        if settings.freshservice_requester_email:
            ticket_payload["email"] = settings.freshservice_requester_email
        if settings.freshservice_workspace_id is not None:
            ticket_payload["workspace_id"] = settings.freshservice_workspace_id

        if current and current[0].get("freshservice_ticket_id"):
            ticket_id = current[0]["freshservice_ticket_id"]
            ticket = await self.client.update_ticket(ticket_id, ticket_payload)
        else:
            ticket = await self.client.create_ticket(ticket_payload)
            ticket_id = ticket.get("id")
            if not ticket_id:
                raise RuntimeError("Freshservice did not return a ticket id")

        now = _now()
        document_status = current[0].get("status", "synced") if current else "synced"
        document = {
            "sync_key": sync_key,
            "freshservice_ticket_id": ticket_id,
            "subject": subject,
            "priority": priority,
            "last_payload": ticket_payload,
            "last_response": ticket,
            "status": document_status,
            "synced_at": now,
            "updated_at": now,
        }

        if current:
            self.sync.update({"sync_key": sync_key}, {"$set": document})
        else:
            self.sync.insert({**document, "created_at": now})

        return document

    @staticmethod
    def _policy_description(event: dict[str, Any]) -> str:
        return (
            "<p><strong>RiskIQ policy governance event</strong></p>"
            f"<p>Policy: {event.get('policy_id')} v{event.get('version')}</p>"
            f"<p>Transition: {event.get('from')} → {event.get('to')}</p>"
            f"<p>Actor: {event.get('actor')}</p>"
            f"<p>Reason: {event.get('reason') or 'Not specified'}</p>"
            f"<p>Occurred at: {event.get('at')}</p>"
        )

    @staticmethod
    def _decision_review_description(event: dict[str, Any]) -> str:
        evidence_hash = str(event.get("evidence_hash") or "")
        justification = str(event.get("justification") or "Not specified")
        evidence = json.dumps(event.get("evidence") or {}, sort_keys=True, default=str)
        return (
            "<p><strong>RiskIQ decision review transition</strong></p>"
            f"<p>Decision: {event.get('decision_id')}</p>"
            f"<p>Review state: {event.get('review_state') or event.get('status')}</p>"
            f"<p>Action: {event.get('action')} ({event.get('action_level')})</p>"
            f"<p>Policy: {event.get('policy_id')} v{event.get('policy_version')}</p>"
            f"<p>Approver/reviewer: {event.get('actor')}</p>"
            f"<p>Justification: {justification}</p>"
            f"<p>Evidence hash: <code>{evidence_hash}</code></p>"
            f"<p>Evidence snapshot: <code>{evidence[:6000]}</code></p>"
        )

    @staticmethod
    def _decision_description(event: dict[str, Any]) -> str:
        evidence = json.dumps(event.get("evidence") or {}, sort_keys=True, default=str)
        return (
            "<p><strong>RiskIQ decision execution</strong></p>"
            f"<p>Decision: {event.get('decision_id')}</p>"
            f"<p>Policy: {event.get('policy_id')} v{event.get('policy_version')}</p>"
            f"<p>Status: {event.get('status')}</p>"
            f"<p>Actor: {event.get('actor')}</p>"
            f"<p>Recommendation: {event.get('recommendation') or ''}</p>"
            f"<p>Evidence: <code>{evidence[:6000]}</code></p>"
        )

    def process_webhook(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Consume a Freshservice webhook without calling Freshservice back."""
        self._ensure_indexes()

        ticket = payload.get("ticket") if isinstance(payload.get("ticket"), dict) else payload
        ticket_id = ticket.get("id") or ticket.get("display_id")
        if ticket_id is None:
            raise ValueError("Freshservice webhook requires ticket.id or ticket.display_id")

        status = ticket.get("status")
        sync_rows = self.sync.find(
            {"freshservice_ticket_id": ticket_id},
            limit=10,
        )

        updated = 0
        for row in sync_rows:
            self.sync.update(
                {"sync_key": row["sync_key"]},
                {
                    "$set": {
                        "freshservice_status": status,
                        "freshservice_updated_at": ticket.get("updated_at"),
                        "last_webhook_at": _now(),
                        "status": "resolved" if str(status).lower() in {"4", "resolved", "closed"} else str(status).lower(),
                        "synced_at": _now(),
                    }
                },
            )
            updated += 1

        return {
            "accepted": True,
            "ticket_id": ticket_id,
            "updated_sync_records": updated,
            "status": status,
        }

    @staticmethod
    def verify_webhook_secret(provided: str | None) -> bool:
        expected = settings.freshservice_webhook_secret
        if not expected:
            return False
        return bool(provided) and hmac.compare_digest(provided, expected)


compliance_service = ComplianceAutomationService()
