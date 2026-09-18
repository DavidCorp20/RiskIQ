# RiskIQ Copilot — Dual Mode

The CRO Copilot now separates interaction intent into two lightweight modes.

## Conversational mode

Used for greetings and general conversation that does not reference portfolio-risk concepts. Gemini receives only the recent conversation and the current question. Portfolio evidence, facts, concentration, vintage data, drivers, and decisions are intentionally omitted from the model context.

This keeps informal interactions natural and avoids sending large or irrelevant analytical payloads.

## Analytical mode

Activated when the question references portfolio-risk concepts such as PAR, DPD, exposure, delinquency, migration, Roll Rate, vintage, concentration, Collections, Underwriting, FPD, decisions, or committee analysis.

Gemini receives deterministic RiskIQ evidence plus relevant supporting context and conversation history. Quantitative claims remain grounded in the deterministic engine.

## API contract

POST /api/v1/ai/copilot remains unchanged for the frontend. The route continues to accept question, dataset_id, risk_facts, drivers, decisions, and conversation, and returns the same JSON response envelope with answer, grounding metadata, and evidence fields.

The response additionally exposes conversation_mode and prompt_version for observability.

## Guardrails

The LLM never becomes the source of calculated risk metrics. It interprets deterministic evidence in analytical mode and receives no portfolio evidence in conversational mode. Migration stress remains conditional and Roll Rate remains historical rather than predictive.
