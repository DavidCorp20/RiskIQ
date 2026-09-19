from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage
from typing import Any

from app.config import settings
from app.risk_events.models import RiskAction, Severity


class EmailNotificationAdapter:
    """SMTP notification adapter for HIGH/CRITICAL risk actions."""

    async def dispatch(self, action: RiskAction | dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
        action_dict = action.model_dump(mode="json") if isinstance(action, RiskAction) else dict(action)
        severity = str(event.get("severity") or "").upper()
        if severity not in {Severity.HIGH.value, Severity.CRITICAL.value}:
            return {"enabled": False, "adapter": "EMAIL", "reason": "severity_not_alertable"}

        if not settings.riskiq_smtp_host or not settings.riskiq_alert_email:
            return {"enabled": False, "adapter": "EMAIL", "reason": "not_configured"}

        await asyncio.to_thread(self._send, action_dict, event)
        return {"enabled": True, "adapter": "EMAIL", "action_id": action_dict["action_id"]}

    @staticmethod
    def _send(action: dict[str, Any], event: dict[str, Any]) -> None:
        msg = EmailMessage()
        msg["Subject"] = f"[RiskIQ][{event.get('severity')}] {event.get('event_type')} | {action.get('action_id')}"
        msg["From"] = settings.riskiq_smtp_from or settings.riskiq_alert_email
        msg["To"] = settings.riskiq_alert_email
        msg.set_content(
            "\n".join([
                "RiskIQ critical action notification",
                f"Event: {event.get('event_id')}",
                f"Severity: {event.get('severity')}",
                f"Metric: {event.get('metric')}",
                f"Observed: {event.get('observed_value')}",
                f"Exposure: {event.get('exposure')}",
                f"Action: {action.get('action_type')}",
                f"Owner: {action.get('owner')}",
                f"Rationale: {action.get('rationale')}",
            ])
        )
        with smtplib.SMTP(settings.riskiq_smtp_host, settings.riskiq_smtp_port, timeout=settings.riskiq_action_timeout_seconds) as smtp:
            if settings.riskiq_smtp_starttls:
                smtp.starttls()
            if settings.riskiq_smtp_username:
                smtp.login(settings.riskiq_smtp_username, settings.riskiq_smtp_password)
            smtp.send_message(msg)
