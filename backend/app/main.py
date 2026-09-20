import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.observability import install_observability

app = FastAPI(
    title="RiskIQ API",
    version="1.0.0",
    description="Credit Risk & Portfolio Decision Intelligence API",
)
install_observability(app)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "riskiq-api"}


from app.api.core_routes import router as core_router
from app.api.analyst_routes import router as analyst_router
from app.api.ai_routes import router as ai_router
from app.api.ews_routes import router as ews_router
from app.predictive.routes import router as predictive_router
from app.stress_testing.routes import router as stress_testing_router
from app.api.audit_routes import router as audit_router
from app.api.data_routes import router as data_router
from app.api.dataset_intelligence_routes import router as dataset_intelligence_router
from app.api.dataset_routes import router as dataset_router
from app.api.decision_card_routes import router as decision_card_router
from app.api.decision_center_routes import router as decision_center_router
from app.api.decision_recommendation_routes import router as decision_recommendation_router
from app.api.decision_routes import router as decision_router
from app.api.diagnosis_routes import router as diagnosis_router
from app.api.governance_routes import router as governance_router
from app.api.history_routes import router as history_router
from app.api.indicator_routes import router as indicator_router
from app.api.intelligence_routes import router as intelligence_router
from app.api.learning_routes import router as learning_router
from app.api.market_routes import router as market_router
from app.api.npl_routes import router as npl_router
from app.api.pipeline_routes import router as pipeline_router
from app.api.policy_metrics_routes import router as policy_metrics_router
from app.api.projection_routes import router as projection_router
from app.api.quality_routes import router as quality_router
from app.api.risk_routes import router as risk_router
from app.api.risk_intelligence_routes import router as risk_intelligence_router
from app.api.risk_event_routes import router as risk_event_router
from app.api.routes import router
from app.api.rule_builder_routes import router as rule_builder_router
from app.api.segment_routes import router as segment_router
from app.api.simulation_routes import router as simulation_router
from app.api.snapshot_routes import router as snapshot_router
from app.api.vintage_routes import router as vintage_router
from app.api.portfolio_routes import router as portfolio_router
from app.api.workspace_routes import router as workspace_router
from app.api.v1.endpoints.smart_ingest import router as smart_ingest_router
from app.reports.routes import router as reports_router


cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "https://riskiq.davidarenascorp.workers.dev,https://riskiq-ivory.vercel.app,http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


for r in [
    router,
    core_router,
    analyst_router,
    data_router,
    dataset_router,
    segment_router,
    dataset_intelligence_router,
    projection_router,
    quality_router,
    diagnosis_router,
    indicator_router,
    risk_router,
    risk_intelligence_router,
    risk_event_router,
    npl_router,
    intelligence_router,
    vintage_router,
    portfolio_router,
    snapshot_router,
    history_router,
    pipeline_router,
    decision_router,
    decision_card_router,
    decision_center_router,
    decision_recommendation_router,
    simulation_router,
    rule_builder_router,
    governance_router,
    policy_metrics_router,
    audit_router,
    learning_router,
    market_router,
    ai_router,
    ews_router,
    predictive_router,
    stress_testing_router,
    workspace_router,
    smart_ingest_router,
    reports_router,
]:
    app.include_router(r, prefix="/api")
