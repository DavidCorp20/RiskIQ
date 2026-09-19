from __future__ import annotations

import os


class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    mongo_url: str = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    mongo_db: str = os.getenv("MONGO_DB", "riskiq_dev")
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")

    # AI
    ai_provider: str = os.getenv("AI_PROVIDER", "gemini")
    ai_model: str = os.getenv("AI_MODEL", "gemini-3.8-flash")
    ai_timeout_seconds: float = float(os.getenv("AI_TIMEOUT_SECONDS", "20"))
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

    # Freshservice compliance automation. Configuration is inert when disabled,
    # so external ITSM availability can never be a startup dependency.
    freshservice_enabled: bool = os.getenv("FRESHSERVICE_ENABLED", "false").lower() == "true"
    freshservice_base_url: str = os.getenv("FRESHSERVICE_BASE_URL", "")
    freshservice_api_key: str = os.getenv("FRESHSERVICE_API_KEY", "")
    freshservice_webhook_secret: str = os.getenv("FRESHSERVICE_WEBHOOK_SECRET", "")
    freshservice_critical_policy_statuses: str = os.getenv(
        "FRESHSERVICE_CRITICAL_POLICY_STATUSES",
        "APPROVED,DEPLOYED,RETIRED",
    )
    freshservice_timeout_seconds: float = float(os.getenv("FRESHSERVICE_TIMEOUT_SECONDS", "8"))
    freshservice_max_retries: int = int(os.getenv("FRESHSERVICE_MAX_RETRIES", "3"))
    freshservice_retry_backoff_seconds: float = float(
        os.getenv("FRESHSERVICE_RETRY_BACKOFF_SECONDS", "0.5")
    )
    freshservice_max_retry_delay_seconds: float = float(
        os.getenv("FRESHSERVICE_MAX_RETRY_DELAY_SECONDS", "30")
    )
    freshservice_max_connections: int = int(os.getenv("FRESHSERVICE_MAX_CONNECTIONS", "10"))
    freshservice_max_keepalive_connections: int = int(
        os.getenv("FRESHSERVICE_MAX_KEEPALIVE_CONNECTIONS", "5")
    )
    freshservice_requester_email: str = os.getenv("FRESHSERVICE_REQUESTER_EMAIL", "")
    freshservice_workspace_id: int | None = (
        int(os.getenv("FRESHSERVICE_WORKSPACE_ID"))
        if os.getenv("FRESHSERVICE_WORKSPACE_ID")
        else None
    )

    # Market intelligence
    market_context_enabled: bool = os.getenv("MARKET_CONTEXT_ENABLED", "true").lower() == "true"
    market_context_cache_ttl_seconds: int = int(os.getenv("MARKET_CONTEXT_CACHE_TTL_SECONDS", "60"))
    market_context_timeout_seconds: float = float(os.getenv("MARKET_CONTEXT_TIMEOUT_SECONDS", "3"))
    market_nq_symbol: str = os.getenv("MARKET_NQ_SYMBOL", "NQ=F")
    market_nq_url: str = os.getenv(
        "MARKET_NQ_URL",
        "https://query1.finance.yahoo.com/v8/finance/chart/NQ=F?range=1d&interval=5m",
    )
    market_fred_api_key: str = os.getenv("MARKET_FRED_API_KEY", "")
    market_fred_series: str = os.getenv("MARKET_FRED_SERIES", "FEDFUNDS,CPIAUCSL,UNRATE")
    market_fred_url: str = os.getenv(
        "MARKET_FRED_URL",
        "https://api.stlouisfed.org/fred/series/observations",
    )

    # Action adapters / notifications
    riskiq_action_adapter: str = os.getenv("RISKIQ_ACTION_ADAPTER", "FRESHSERVICE")
    riskiq_action_webhook_url: str = os.getenv("RISKIQ_ACTION_WEBHOOK_URL", "")
    riskiq_action_webhook_secret: str = os.getenv("RISKIQ_ACTION_WEBHOOK_SECRET", "")
    riskiq_action_timeout_seconds: float = float(os.getenv("RISKIQ_ACTION_TIMEOUT_SECONDS", "8"))
    riskiq_action_max_retries: int = int(os.getenv("RISKIQ_ACTION_MAX_RETRIES", "3"))
    riskiq_action_retry_backoff_seconds: float = float(
        os.getenv("RISKIQ_ACTION_RETRY_BACKOFF_SECONDS", "0.5")
    )
    riskiq_action_max_retry_delay_seconds: float = float(
        os.getenv("RISKIQ_ACTION_MAX_RETRY_DELAY_SECONDS", "30")
    )

    smtp_host: str = os.getenv("RISKIQ_SMTP_HOST", "")
    smtp_port: int = int(os.getenv("RISKIQ_SMTP_PORT", "587"))
    smtp_username: str = os.getenv("RISKIQ_SMTP_USERNAME", "")
    smtp_password: str = os.getenv("RISKIQ_SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("RISKIQ_SMTP_FROM", "")
    smtp_starttls: bool = os.getenv("RISKIQ_SMTP_STARTTLS", "true").lower() == "true"
    alert_email: str = os.getenv("RISKIQ_ALERT_EMAIL", "")

    sentry_dsn: str = os.getenv("SENTRY_DSN", "")
    sentry_traces_sample_rate: float = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.05"))
    performance_warning_ms: float = float(os.getenv("RISKIQ_PERFORMANCE_WARNING_MS", "3000"))


settings = Settings()
