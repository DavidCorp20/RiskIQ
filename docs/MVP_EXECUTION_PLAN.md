# RiskIQ — MVP Execution Plan

## Product north star

RiskIQ converts heterogeneous financial portfolio data into understandable analysis, evidence-based diagnosis, and configurable decisions.

**Core flow:**

`Source → Data Quality → Normalize → Indicators → Analysis Models → Diagnosis → AI assistance → Policy → Decision → Report`

## MVP definition

The MVP is complete when an analyst or manager can:

1. Load a portfolio from Excel/CSV or refresh from a supported SQL source.
2. See the source data and data-quality errors/warnings.
3. Map source fields into a reusable canonical financial model.
4. Run core portfolio indicators.
5. Select a predefined analysis model.
6. Read an evidence-backed diagnosis.
7. Ask the AI Copilot for explanation / next-best-analysis guidance.
8. Build a custom indicator with safe formulas.
9. Create and validate a monitoring policy.
10. Simulate the policy before activation.
11. See the resulting decision with evidence.
12. Generate an executive or analyst report.

## Current state

### Advanced / already present

- FastAPI backend and modular route architecture.
- Dataset persistence and portfolio records.
- Deterministic PAR7/30/60/90 analytics.
- Portfolio intelligence and risk intelligence.
- Concentration, vintage and roll-rate foundations.
- Snapshot/history handling.
- Initial decision engine with evidence and human review.
- Rule builder validation / compilation / evaluation.
- Safe formula engine.
- Scorecard evaluation.
- Portfolio simulation and historical replay foundations.
- AI Copilot foundation.
- Governance/audit route foundations.

### Partial

- Universal financial data model.
- Data discovery and mapping UX.
- Data-quality workspace with row/column corrections.
- Diagnosis quality and root-cause depth.
- Indicator Builder UX.
- Analysis Model Library UX.
- Policy Builder UX.
- Decision Center as an operational workflow.
- Reporting.
- Roles and permissions.
- End-to-end product flow.

### Future / not MVP

- Full Monte Carlo methodology.
- Advanced predictive models.
- Streaming / CDC.
- Broad warehouse connector ecosystem.
- External action automation.
- Originations / underwriting.
- CRM / collections execution.

## Execution phases

### Phase 1 — Product flow closure

Goal: make one complete path work from dataset to decision.

Deliverables:

- clear workspace stages;
- dataset status;
- data-quality summary;
- analysis readiness;
- diagnosis;
- decision summary;
- report entry point.

### Phase 2 — Universal data foundation

Deliverables:

- canonical field registry;
- source-to-canonical mappings;
- instrument types;
- mapping persistence;
- quality impact on model readiness;
- refresh-under-demand contract for SQL sources.

### Phase 3 — Analytics engine

Deliverables:

- indicator catalog;
- indicator readiness;
- indicator builder v1;
- core analysis models;
- model prerequisites and limitations.

### Phase 4 — Diagnosis + AI

Deliverables:

- evidence cards;
- driver ranking;
- confidence and limitations;
- next-best-analysis guidance;
- grounded Copilot responses.

### Phase 5 — Decision & Policy Engine

Deliverables:

- policy builder;
- versioning;
- validation;
- simulation;
- activation state;
- deterministic evaluation;
- evidence-linked decision result.

### Phase 6 — Reporting + governance

Deliverables:

- executive report;
- analyst report;
- organization / entity / user model;
- roles and permissions;
- audit trail.

### Phase 7 — MVP acceptance

Acceptance criterion:

A real analyst can complete the core flow without developer intervention and explain the portfolio diagnosis, evidence, recommendation and configured policy to a manager.

## Product discipline

RiskIQ should not add a new module unless it improves one of these outcomes:

- understand the data;
- analyze the portfolio;
- diagnose a problem;
- make a decision;
- document or communicate the decision.

Advanced analytics such as Monte Carlo, forecasting, Markov/transition models, survival analysis, bootstrap, VaR/CVaR and optimization belong in the analysis-model architecture, but only become MVP scope when validated against a real customer use case and supported by adequate data.
