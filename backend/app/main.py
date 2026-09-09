from fastapi import FastAPI

from app.api.ai_routes import router as ai_router
from app.api.audit_routes import router as audit_router
from app.api.data_routes import router as data_router
from app.api.decision_card_routes import router as decision_card_router
from app.api.decision_routes import router as decision_router
from app.api.intelligence_routes import router as intelligence_router
from app.api.learning_routes import router as learning_router
from app.api.projection_routes import router as projection_router
from app.api.quality_routes import router as quality_router
from app.api.risk_routes import router as risk_router
from app.api.routes import router
from app.api.rule_builder_routes import router as rule_builder_router
from app.api.simulation_routes import router as simulation_router
from app.api.snapshot_routes import router as snapshot_router
from app.api.vintage_routes import router as vintage_router

app = FastAPI(
    title="RiskIQ API",
    version="0.1.0",
    description="Credit Risk & Portfolio Decision Intelligence API",
)

app.include_router(router, prefix="/api")
app.include_router(data_router, prefix="/api")
app.include_router(projection_router, prefix="/api")
app.include_router(quality_router, prefix="/api")
app.include_router(risk_router, prefix="/api")
app.include_router(intelligence_router, prefix="/api")
app.include_router(vintage_router, prefix="/api")
app.include_router(snapshot_router, prefix="/api")
app.include_router(decision_router, prefix="/api")
app.include_router(decision_card_router, prefix="/api")
app.include_router(simulation_router, prefix="/api")
app.include_router(rule_builder_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(learning_router, prefix="/api")
app.include_router(ai_router, prefix="/api")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "riskiq-api"}
