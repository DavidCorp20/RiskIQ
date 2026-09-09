from __future__ import annotations

import os


class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    mongo_url: str = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    mongo_db: str = os.getenv("MONGO_DB", "riskiq_dev")
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")


settings = Settings()
