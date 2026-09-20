# RiskIQ — Fase 1: Base de producto y definición del núcleo

Núcleo: datos -> normalización -> métricas -> hechos -> reglas -> decisión -> acción -> auditoría.

La Fase 1 introduce contratos canónicos sin reemplazar los servicios existentes. RiskAnalyticsService calcula métricas; DecisionEngine evalúa reglas; RiskCorePipeline orquesta el orden y entrega un envelope estable.

Entidades: PortfolioObservationContract, RiskMetricContract, RiskFactContract, DecisionContract, AuditEventContract y RiskRunContract.

Contrato HTTP: POST /api/v1/core/run. Es stateless y no ejecuta acciones externas; devuelve métricas, hechos, decisión y auditoría en risk-core-v1.

Principios: no duplicar motores; AI no calcula; acciones externas quedan fuera del núcleo; compatibilidad con FastAPI/MongoDB; migración gradual sin big-bang refactor.

Fase 2: persistencia de RiskRun, idempotency keys, tenant isolation, contract tests HTTP y separación explícita suggested/approved/executed.
