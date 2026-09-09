from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="RiskIQ API",
    version="0.1.0",
    description="Credit Risk & Portfolio Decision Intelligence API",
)

app.include_router(router, prefix="/api")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "riskiq-api"}
