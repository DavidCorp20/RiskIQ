# RiskIQ Institutional Integration Quickstart

## 1. Production API

Base URL:

`https://riskiq-api-v2-production.up.railway.app`

FastAPI exposes the interactive OpenAPI contract at:

- `/docs`
- `/redoc`
- `/openapi.json`

Runtime contracts:

- `GET /health` — liveness.
- `GET /ready` — readiness and dependency state.
- `GET /version` — service version and contract version.

The unified intelligence contract is:

`GET /api/v1/risk-intelligence/{dataset_id}`

The response identifies itself with:

`contract_version: risk-intelligence-v1`

and declares deterministic calculated fields with:

`ai_mutable_fields: []`

## 2. Dataset ingestion

RiskIQ accepts CSV/XLSX through the Smart Ingestion flow.

Primary endpoint:

`POST /api/v1/data/smart-ingest`

The ingestion pipeline is:

`Discovery -> Semantic Mapping -> Data Quality -> Readiness -> Persistence/Analysis`

Maximum upload size is 25 MB.

### Canonical portfolio fields

Common canonical fields include:

- `customer_id`
- `loan_id`
- `product_id`
- `origination_date`
- `due_date`
- `snapshot_date`
- `scheduled_amount`
- `paid_amount`
- `outstanding_principal`
- `status`
- `segment`
- `dpd`
- `pd`
- `lgd`
- `ead`

The mapper supports deterministic aliases, fuzzy matching and optional AI enrichment for unresolved columns.

## 3. Deterministic risk intelligence

After ingestion, the main contract is:

`GET /api/v1/risk-intelligence/{dataset_id}`

The payload can contain:

- portfolio analytics
- PAR30/PAR60/PAR90
- NPL
- concentration
- vintage
- risk drivers
- observed transition matrix
- PD ratings
- survival analysis
- market context
- risk events/actions
- stress-testing baseline
- evidence hash

The API explicitly marks the contract as deterministic. AI must interpret evidence rather than mutate calculated values.

## 4. Evidence integrity

DSI export:

`POST /api/v1/reports/dsi-export`

Verification:

`GET /api/v1/reports/verify/{evidence_hash}`

The DSI evidence package includes a SHA-256 `evidence_hash`. Verification is expected to return:

- `verified: true`
- `tamper_detected: false`

for an unchanged evidence package.

## 5. Macro stress testing

General stress endpoint:

`POST /api/v1/stress-testing/run`

Macro Stress Testing 2.0:

`POST /api/v1/stress-testing/macro-v2`

Supported regional profiles include LATAM stress profiles. The stress engine is deterministic and should be interpreted as a scenario/sensitivity analysis unless validated predictive sensitivities are explicitly supplied.

## 6. Governance and Freshservice

RiskIQ governance events are persisted before external synchronization.

Critical policy transitions are sent to the compliance outbox. Decision execution events can also generate/update Freshservice tickets.

Freshservice configuration:

- `FRESHSERVICE_ENABLED`
- `FRESHSERVICE_BASE_URL`
- `FRESHSERVICE_API_KEY`
- `FRESHSERVICE_WEBHOOK_SECRET`
- `FRESHSERVICE_REQUESTER_EMAIL`
- `FRESHSERVICE_WORKSPACE_ID`

The synchronization layer uses asynchronous HTTP, connection reuse, bounded retries for transient network/provider failures, and a Mongo-backed outbox.

Webhook endpoint:

`POST /api/v1/audit/freshservice/webhook`

Accepted authentication forms:

- `X-RiskIQ-Webhook-Secret`
- `Authorization: Bearer <secret>`

RiskIQ does not call Freshservice back while processing an inbound webhook.

## 7. Audit / compliance status

Freshservice synchronization status:

`GET /api/v1/audit/freshservice/status`

Manual outbox synchronization:

`POST /api/v1/audit/freshservice/sync`

Decision audit:

`POST /api/v1/audit/decisions`

Decision history:

`GET /api/v1/audit/decisions`

## 8. Institutional integration pattern

Recommended enterprise flow:

`Client/Core -> Dataset Ingestion -> RiskIQ Evidence -> Risk Intelligence -> Decision/Policy -> Audit -> ITSM/Webhook`

For production integrations, clients should:

1. Treat `risk-intelligence-v1` as the versioned analytical contract.
2. Persist `evidence_hash` alongside downstream decisions.
3. Store `dataset_id`, `snapshot_id`, policy ID/version and decision ID for traceability.
4. Use HTTPS only.
5. Store API credentials/secrets outside source control.
6. Validate webhook signatures/secrets before accepting external events.
7. Keep deterministic RiskIQ evidence separate from AI-generated interpretation.

## 9. OpenAPI

The authoritative API specification is generated directly by FastAPI and is available from the production service at:

`/openapi.json`

This avoids maintaining a second manually edited OpenAPI document that could drift from the implementation.
