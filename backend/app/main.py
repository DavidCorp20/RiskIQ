from fastapi import FastAPI

from app.api.data_routes import router as data_router
from app.api.routes import router

app = FastAPI(
    title="RiskIQ API",
    version="0.1.0",
    description="Credit Risk & Portfolio Decision Intelligence API",
)

app.include_router(router, prefix="/api")
app.include_router(data_router, prefix="/api")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "riskiq-api"}
