from __future__ import annotations
import os

def _optional_int(name: str) -> int | None:
    value=os.getenv(name,"").strip()
    if not value:return None
    try:return int(value)
    except (TypeError, ValueError):return None

def _float(name: str, default: float) -> float:
    try:return float(os.getenv(name,str(default)))
    except (TypeError, ValueError):return default

def _int(name: str, default: int) -> int:
    try:return int(os.getenv(name,str(default)))
    except (TypeError, ValueError):return default

class Settings:
    app_env: str=os.getenv("APP_ENV","development")
    mongo_url: str=os.getenv("MONGO_URL","mongodb://localhost:27017")
    mongo_db: str=os.getenv("MONGO_DB","riskiq_dev")
    cors_origins: str=os.getenv("CORS_ORIGINS","http://localhost:5173")
    freshservice_enabled: bool=os.getenv("FRESHSERVICE_ENABLED","false").lower()=="true"
    freshservice_base_url: str=os.getenv("FRESHSERVICE_BASE_URL","")
    freshservice_api_key: str=os.getenv("FRESHSERVICE_API_KEY","")
    freshservice_webhook_secret: str=os.getenv("FRESHSERVICE_WEBHOOK_SECRET","")
    freshservice_requester_email: str=os.getenv("FRESHSERVICE_REQUESTER_EMAIL","")
    freshservice_workspace_id: int|None=_optional_int("FRESHSERVICE_WORKSPACE_ID")
    freshservice_critical_policy_statuses: str=os.getenv("FRESHSERVICE_CRITICAL_POLICY_STATUSES","APPROVED,DEPLOYED,RETIRED")
    freshservice_timeout_seconds: float=_float("FRESHSERVICE_TIMEOUT_SECONDS",8)
    freshservice_max_retries: int=_int("FRESHSERVICE_MAX_RETRIES",3)
    freshservice_retry_backoff_seconds: float=_float("FRESHSERVICE_RETRY_BACKOFF_SECONDS",0.5)
    freshservice_max_retry_delay_seconds: float=_float("FRESHSERVICE_MAX_RETRY_DELAY_SECONDS",30)
    freshservice_max_connections: int=_int("FRESHSERVICE_MAX_CONNECTIONS",10)
    freshservice_max_keepalive_connections: int=_int("FRESHSERVICE_MAX_KEEPALIVE_CONNECTIONS",5)
    dsi_audit_signing_secret: str=os.getenv("DSI_AUDIT_SIGNING_SECRET","")

    # Provider-agnostic Action Layer
    riskiq_action_adapter: str=os.getenv("RISKIQ_ACTION_ADAPTER","FRESHSERVICE" if freshservice_enabled else "INTERNAL")
    riskiq_action_webhook_url: str=os.getenv("RISKIQ_ACTION_WEBHOOK_URL","")
    riskiq_action_webhook_secret: str=os.getenv("RISKIQ_ACTION_WEBHOOK_SECRET","")
    riskiq_action_timeout_seconds: float=_float("RISKIQ_ACTION_TIMEOUT_SECONDS",8)
    riskiq_action_max_retries: int=_int("RISKIQ_ACTION_MAX_RETRIES",3)
    riskiq_action_retry_backoff_seconds: float=_float("RISKIQ_ACTION_RETRY_BACKOFF_SECONDS",0.5)
    riskiq_action_max_retry_delay_seconds: float=_float("RISKIQ_ACTION_MAX_RETRY_DELAY_SECONDS",30)

    # SMTP notifications
    riskiq_smtp_host: str=os.getenv("RISKIQ_SMTP_HOST","")
    riskiq_smtp_port: int=_int("RISKIQ_SMTP_PORT",587)
    riskiq_smtp_username: str=os.getenv("RISKIQ_SMTP_USERNAME","")
    riskiq_smtp_password: str=os.getenv("RISKIQ_SMTP_PASSWORD","")
    riskiq_smtp_from: str=os.getenv("RISKIQ_SMTP_FROM","")
    riskiq_smtp_starttls: bool=os.getenv("RISKIQ_SMTP_STARTTLS","true").lower()=="true"
    riskiq_alert_email: str=os.getenv("RISKIQ_ALERT_EMAIL","")

    # Runtime observability
    sentry_dsn: str=os.getenv("SENTRY_DSN","")
    sentry_traces_sample_rate: float=_float("SENTRY_TRACES_SAMPLE_RATE",0.05)
    riskiq_performance_warning_ms: int=_int("RISKIQ_PERFORMANCE_WARNING_MS",3000)

settings=Settings()
