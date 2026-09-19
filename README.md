# RiskIQ

## Credit Risk & Portfolio Decision Intelligence

RiskIQ convierte datos de cartera en decisiones de riesgo accionables.

**Data → Analysis → Diagnostic → Decision → Action**

## Objetivo

Construir una plataforma B2B para instituciones financieras, fintechs, cooperativas, microfinancieras y equipos de riesgo que permita conectar datos de crédito, normalizarlos, analizar la cartera, identificar causas y convertir los hallazgos en decisiones automatizables.

## Principios del producto

- El motor analítico calcula hechos; la IA interpreta esos hechos.
- Las reglas son declarativas, versionables y auditables.
- No se ejecuta código arbitrario del cliente.
- Las decisiones pueden ser manuales, sugeridas, sujetas a aprobación o automáticas.
- Todo resultado relevante debe poder explicarse con evidencia.
- El sistema debe funcionar con Excel/CSV inicialmente y evolucionar hacia PostgreSQL, APIs, data warehouses y core systems.

## Módulos

1. Data Discovery
2. Data Mapping
3. Data Quality
4. Universal Portfolio Model
5. Portfolio Intelligence
6. Risk Analytics
7. Root Cause / Risk Drivers
8. Decision Engine
9. Low-Code Decision Builder
10. Automation Engine
11. AI Decision Copilot
12. Scenario Simulator
13. Decision Center
14. Audit & Decision History

## Indicadores iniciales

- DPD
- PAR 7/30/60/90
- NPL
- Vintage
- Roll Rates
- Default Rate
- Recovery Rate
- Exposure
- Concentration
- Originations
- Collections
- Portfolio Health

## Decision Engine

El núcleo del producto seguirá este flujo:

```text
Data
  ↓
Normalization
  ↓
Metrics
  ↓
Facts
  ↓
Rules
  ↓
Decision
  ↓
Action
  ↓
Audit
```

Ejemplo:

```text
WHEN PAR30 > 8%
AND segment = "C"
THEN
  risk_level = "HIGH"
  create_alert = true
  recommendation = "REVIEW_ORIGINATION"
```

## Low-Code Decision Builder

El producto evolucionará hacia tres niveles:

### Nivel 1 — Visual

Constructor de condiciones y acciones para usuarios de negocio.

### Nivel 2 — Fórmulas

Editor controlado con funciones como `IF`, `AND`, `OR`, `SUM`, `AVG`, `CHANGE`, `GROWTH`, `PERCENTILE` y funciones específicas de riesgo.

### Nivel 3 — Risk DSL

Lenguaje declarativo controlado para usuarios avanzados.

La IA podrá transformar lenguaje natural en una regla propuesta, pero la regla deberá ser validada por el usuario antes de activarse.

## Arquitectura objetivo

```text
Frontend
   ↓
API
   ↓
Data Layer ─── Portfolio Model
   ↓
Analytics Engine
   ↓
Decision Engine
   ├── Rules
   ├── Formula Engine
   ├── Automation
   └── Audit
   ↓
AI Copilot / Simulator / Decision Center
```

## Roadmap

### Phase 1 — Core Foundation

- Repository architecture
- Backend API foundation
- Universal data model
- CSV/Excel ingestion contract
- Data validation
- Core risk metrics
- Declarative rule schema
- Decision engine foundation
- Audit model
- Tests

### Phase 2 — Portfolio Intelligence

- Portfolio dashboard
- Segmentation
- Vintage analysis
- Roll rates
- Concentration
- Collections analytics
- Risk drivers

### Phase 3 — Decision Builder

- Visual rule builder
- Formula builder
- Rule validation
- Versioning
- Activation/deactivation
- Simulation before activation

### Phase 4 — Automation

- Scheduled evaluations
- Alerts
- Tasks
- Notifications
- Approval workflows
- Automatic actions

### Phase 5 — AI Copilot

- Natural-language analysis
- Rule generation proposals
- Explainability
- Decision summaries
- Evidence-based recommendations

### Phase 6 — Simulation & Predictive Risk

- Scenario engine
- What-if analysis
- Predictive models
- Collections optimization
- Portfolio forecasting

## Quality standard

RiskIQ no debe convertirse en un dashboard desechable. Cada módulo debe construirse como una pieza reutilizable del producto final, con contratos claros, validaciones, pruebas y trazabilidad.
