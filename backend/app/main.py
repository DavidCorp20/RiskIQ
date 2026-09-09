from fastapi import FastAPI

from app.api.data_routes import router as data_router
from app.api.decision_routes import router as decision_router
from app.api.intelligence_routes import router as intelligence_router
from app.api.risk_routes import router as risk_router
from app.api.routes import router
from app.api.vintage_routes import router as vintage_router

app = FastAPI(
    title="RiskIQ API",
    version="0.1.0",
    description="Credit Risk & Portfolio Decision Intelligence API",
)

app.include_router(router, prefix="/api")
app.include_router(data_router, prefix="/api")
app.include_router(risk_router, prefix="/api")
app.include_router(intelligence_router, prefix="/api")
app.include_router(vintage_router, prefix="/api")
app.include_router(decision_router, prefix="/api")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "riskiq-api"}
