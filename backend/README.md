# RiskIQ Backend

Backend foundation for the RiskIQ platform.

## Responsibilities

- API and tenant boundaries
- Data ingestion orchestration
- Portfolio domain services
- Risk metric calculation
- Declarative decision evaluation
- Automation orchestration
- Audit events
- AI adapter integration

## Domain separation

```text
backend/
├── api/          # HTTP contracts
├── domain/       # business entities and rules
├── services/     # application services
├── infrastructure/ # database, files, external providers
└── tests/
```

The backend must keep business logic outside route handlers. Routes translate HTTP requests into application-service calls.
