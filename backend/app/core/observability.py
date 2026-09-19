from __future__ import annotations

import json
import logging
import os
import time
import uuid
from contextvars import ContextVar
from typing import Any

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }
        dataset_id = getattr(record, "dataset_id", None)
        if dataset_id:
            payload["dataset_id"] = dataset_id
        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def configure_sentry() -> None:
    if not settings.sentry_dsn:
        return
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[FastApiIntegration(), StarletteIntegration()],
        traces_sample_rate=settings.sentry_traces_sample_rate,
        environment=settings.app_env,
        send_default_pii=False,
    )


def _memory_kb() -> int:
    # Railway runs Linux; /proc gives current resident memory without a third-party profiler.
    try:
        with open("/proc/self/status", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except (OSError, ValueError):
        pass
    return 0


class RiskIQObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        memory_before = _memory_kb()
        dataset_id = request.query_params.get("dataset_id") or request.path_params.get("dataset_id")
        logger = logging.getLogger("riskiq.request")
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            try:
                import sentry_sdk
                sentry_sdk.set_tag("request_id", request_id)
                if dataset_id:
                    sentry_sdk.set_tag("dataset_id", dataset_id)
                sentry_sdk.capture_exception(exc)
            except ImportError:
                pass
            logger.exception("unhandled_request_exception", extra={"dataset_id": dataset_id})
            raise
        finally:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            memory_delta_kb = max(0, _memory_kb() - memory_before)
            if "response" in locals():
                response.headers["X-Request-ID"] = request_id
                response.headers["X-RiskIQ-Latency-MS"] = str(elapsed_ms)
                response.headers["X-RiskIQ-Memory-Delta-KB"] = str(memory_delta_kb)
                if elapsed_ms > settings.performance_warning_ms:
                    response.headers["X-RiskIQ-Performance-Warning"] = f"latency_ms={elapsed_ms}"
            logger.info(
                "request_complete",
                extra={"dataset_id": dataset_id, "latency_ms": elapsed_ms, "memory_delta_kb": memory_delta_kb},
            )
            request_id_ctx.reset(token)


def install_observability(app: FastAPI) -> None:
    configure_logging()
    configure_sentry()
    app.add_middleware(RiskIQObservabilityMiddleware)
