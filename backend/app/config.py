from __future__ import annotations
import os

def _optional_int(name: str) -> int | None:
    value=os.getenv(name,"").strip()
    if not value:return None
    try:return int(value)
    except ValueError as exc:raise ValueError(f"{name} must be an integer when provided") from exc

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
    freshservice_timeout_seconds: float=float(os.getenv("FRESHSERVICE_TIMEOUT_SECONDS","8"))
    freshservice_max_retries: int=int(os.getenv("FRESHSERVICE_MAX_RETRIES","3"))
    freshservice_retry_backoff_seconds: float=float(os.getenv("FRESHSERVICE_RETRY_BACKOFF_SECONDS","0.5"))
    freshservice_max_retry_delay_seconds: float=float(os.getenv("FRESHSERVICE_MAX_RETRY_DELAY_SECONDS","30"))
    freshservice_max_connections: int=int(os.getenv("FRESHSERVICE_MAX_CONNECTIONS","10"))
    freshservice_max_keepalive_connections: int=int(os.getenv("FRESHSERVICE_MAX_KEEPALIVE_CONNECTIONS","5"))
    dsi_audit_signing_secret: str=os.getenv("DSI_AUDIT_SIGNING_SECRET","")

settings=Settings()
