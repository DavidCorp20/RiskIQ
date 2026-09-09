# RiskIQ Architecture

## 1. Product architecture

```text
                    ┌──────────────────────────┐
                    │        RiskIQ UI         │
                    │ Dashboard / Data / Rules │
                    │ Decisions / AI / Simulate│
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │        API Layer         │
                    │ Auth / Tenancy / REST   │
                    └────────────┬─────────────┘
                                 │
             ┌───────────────────┼───────────────────┐
             ▼                   ▼                   ▼
      ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
      │ Data Layer   │   │ Risk Engine  │   │ Decision     │
      │              │   │              │   │ Engine       │
      │ ingestion    │   │ metrics      │   │ rules        │
      │ mapping      │   │ segmentation │   │ formulas     │
      │ validation   │   │ diagnostics   │   │ automation   │
      └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
             │                  │                  │
             └──────────────────┼──────────────────┘
                                ▼
                     ┌─────────────────────┐
                     │ Decision / Evidence │
                     │ History / Audit     │
                     └──────────┬──────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
             ┌─────────────┐       ┌─────────────┐
             │ AI Copilot  │       │ Simulator   │
             └─────────────┘       └─────────────┘
```

## 2. Architectural rules

### Analytics owns facts

Risk metrics must be calculated deterministically by backend code. The AI layer receives structured evidence and may explain, summarize, compare or recommend, but it must not invent portfolio values.

### Decisions are declarative

A rule is stored as structured data rather than executable customer code. This makes the same decision definition usable by the visual builder, formula builder, API and AI proposal layer.

### Tenant isolation

Every customer-owned object must have a tenant/business scope. No query should rely on a global dataset when tenant context is required.

### Auditability

Rule creation, updates, activation, evaluation and resulting actions must be traceable.

## 3. Universal portfolio model

The initial canonical model will support:

```text
Tenant
 ├── Portfolio
 │    ├── Customer
 │    ├── Product
 │    ├── Account / Obligation
 │    ├── Payment
 │    ├── Collection Event
 │    └── Snapshot
 ├── Data Source
 ├── Rule
 ├── Decision
 ├── Alert
 └── Audit Event
```

The ingestion layer maps institution-specific columns into this canonical model.

## 4. Decision lifecycle

```text
DRAFT
  ↓
VALIDATED
  ↓
SIMULATED
  ↓
APPROVAL_REQUIRED ──→ APPROVED
                         ↓
                      ACTIVE
                         ↓
                     EVALUATED
                         ↓
              ┌──────────┴──────────┐
              ▼                     ▼
          NO_ACTION              ACTION
                                      ↓
                                    AUDIT
```

Rules can also be configured for recommendation-only mode without automatic execution.

## 5. Rule representation

Example conceptual representation:

```json
{
  "name": "High PAR30 segment alert",
  "status": "active",
  "mode": "automatic",
  "conditions": [
    {"metric": "par30", "operator": ">", "value": 0.08},
    {"field": "segment", "operator": "=", "value": "C"}
  ],
  "actions": [
    {"type": "set_risk_level", "value": "HIGH"},
    {"type": "create_alert", "severity": "high"},
    {"type": "create_recommendation", "code": "REVIEW_ORIGINATION"}
  ]
}
```

The exact schema will be implemented in the engine package and versioned as the product evolves.

## 6. Technology direction

Initial target stack:

- Frontend: React + TypeScript
- Backend: Python + FastAPI
- Data processing: pandas / typed domain services
- Database: PostgreSQL for transactional product data
- Object storage: compatible storage for uploaded source files
- Background jobs: queue-based worker architecture
- AI: provider-agnostic adapter
- Deployment: containerized services

MongoDB remains possible for selected document-oriented workloads, but the initial product model favors PostgreSQL because RiskIQ requires relational portfolio analytics, tenant isolation, auditability and transactional consistency.

## 7. Non-goals for the foundation

- Arbitrary Python execution by customers
- Black-box AI decisions
- Fake predictive outputs without a validated model
- Direct database access from frontend
- Business rules embedded inside UI components
- Metrics calculated independently by multiple modules
