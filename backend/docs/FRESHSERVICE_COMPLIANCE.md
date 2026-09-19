# RiskIQ Freshservice Compliance Automation

## What is implemented

RiskIQ now emits durable compliance events for:
- critical policy lifecycle transitions (APPROVED, DEPLOYED, RETIRED by default);
- critical decision/audit executions with triggered rules, automatic mode, approval-required mode, or critical status.

Events are written to MongoDB first and then synchronized asynchronously with Freshservice. A failure does not block the RiskIQ decision/policy request.

Each event is idempotent:
- policy: policy:{policy_id}:v{version}
- decision: decision:{decision_id}

The local sync ledger stores the Freshservice ticket ID so later events update the same ticket instead of creating duplicates.

## Environment variables

~~~text
FRESHSERVICE_ENABLED=true
FRESHSERVICE_BASE_URL=https://YOUR_DOMAIN.freshservice.com
FRESHSERVICE_API_KEY=YOUR_API_KEY
FRESHSERVICE_WEBHOOK_SECRET=YOUR_RANDOM_SECRET
FRESHSERVICE_REQUESTER_EMAIL=YOUR_RISKIQ_SERVICE_ACCOUNT_EMAIL
FRESHSERVICE_WORKSPACE_ID=
FRESHSERVICE_CRITICAL_POLICY_STATUSES=APPROVED,DEPLOYED,RETIRED
FRESHSERVICE_TIMEOUT_SECONDS=8
FRESHSERVICE_MAX_RETRIES=3
FRESHSERVICE_RETRY_BACKOFF_SECONDS=0.5
FRESHSERVICE_MAX_RETRY_DELAY_SECONDS=30
FRESHSERVICE_MAX_CONNECTIONS=10
FRESHSERVICE_MAX_KEEPALIVE_CONNECTIONS=5
~~~

Freshservice API v2 uses HTTPS and API-key Basic Authentication (api_key:X). RiskIQ keeps the key server-side and never sends it to the browser.

## Ticket synchronization

RiskIQ uses POST /api/v2/tickets when a compliance event has no Freshservice ticket yet, and PUT /api/v2/tickets/{id} for subsequent updates.

Tickets receive RiskIQ tags and custom fields such as policy ID/version or decision ID.

The requester email is configurable because Freshservice ticket creation may require a requester/contact identity.

## Freshservice -> RiskIQ webhook

Endpoint:
~~~text
POST /api/v1/audit/freshservice/webhook
~~~

Authentication:
~~~text
X-RiskIQ-Webhook-Secret: <FRESHSERVICE_WEBHOOK_SECRET>
~~~

or:
~~~text
Authorization: Bearer <FRESHSERVICE_WEBHOOK_SECRET>
~~~

The webhook does not call Freshservice back. It updates RiskIQ's local synchronization ledger with the latest Freshservice ticket status and timestamp.

In Freshservice Workflow Automator, configure a webhook that POSTs ticket updates to the RiskIQ endpoint.

## Operational behavior

- 2xx Freshservice responses are accepted.
- 429/500/502/503/504 are retried with exponential backoff.
- Retry-After is honored for rate-limit responses.
- Network/timeouts are retried.
- Failed outbox events remain in MongoDB with status=retry and error metadata.
- Requests to RiskIQ do not wait for the Freshservice call; the event is queued before the response.
- The integration can be disabled completely with FRESHSERVICE_ENABLED=false.

## Production activation

1. Create a dedicated Freshservice API key/service identity.
2. Configure the Railway variables above.
3. Use a dedicated requester email that Freshservice recognizes.
4. Configure the Freshservice Workflow Automator webhook callback.
5. Test a policy transition to APPROVED or DEPLOYED.
6. Confirm one Freshservice ticket is created.
7. Repeat the same transition event and confirm the same ticket is updated rather than duplicated.
8. Execute a decision with a triggered rule and confirm a decision compliance ticket is created.
9. Change the Freshservice ticket and confirm the webhook updates RiskIQ's local sync record.