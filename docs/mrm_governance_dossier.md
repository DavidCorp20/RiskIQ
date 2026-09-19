# RiskIQ — Model Risk Management Governance Dossier

**Contract:** MRM-RISKIQ-v1  
**Scope:** deterministic risk engines, AI Copilot guardrails, DSI evidence integrity and operational governance.

## 1. Model inventory

| Engine | Method | Deterministic | AI mutation allowed |
|---|---|---:|---:|
| Roll Rate / Transition | Observed Markov-style transition matrix | Yes | No |
| PD projection | Matrix power over observed transition probabilities | Yes | No |
| Kaplan-Meier | Non-parametric survival estimator | Yes | No |
| Risk Analytics | PAR/NPL/exposure/concentration/vintage | Yes | No |
| Stress Testing | Scenario sensitivity engine | Yes | No |
| Risk Intelligence | Unified evidence contract | Yes | No |
| Copilot | LLM interpretation of evidence | No | No mutation |

The analytical source of truth remains the deterministic engine. The Copilot is an interpretation layer.

## 2. Roll Rate transition matrix

RiskIQ buckets DPD into:

1. current: DPD < 1
2. early_1_29: 1 <= DPD < 30
3. early_30_59: 30 <= DPD < 60
4. late_60_89: 60 <= DPD < 90
5. hard_90_plus: DPD >= 90

For each observed loan sequence, consecutive snapshots define a transition i -> j.

The empirical transition probability is:

P_ij = N_ij / sum_j(N_ij)

where N_ij is the observed count of transitions from state i to state j.

The engine is implemented in backend/app/predictive/transition_engine.py and uses vectorized pandas/numpy operations.

### Matrix-power PD projection

For a horizon of h periods:

P^(h) = P^h

RiskIQ reports the probability of reaching hard_90_plus from each starting state:

PD_i(h) = P^h_(i,hard90+)

This is a deterministic projection from observed transition behavior. It is not a supervised ML forecast.

## 3. Kaplan-Meier survival

For ordered event times t_j, with d_j observed events and n_j entities at risk immediately before t_j:

S_hat(t) = product over t_j <= t of (1 - d_j / n_j)

RiskIQ implements this in backend/app/predictive/survival_engine.py using vectorized numpy operations.

The output contains period, at-risk population, events and survival probability.

### Hazard interpretation

The current production survival engine exposes the Kaplan-Meier survival curve. A separate statistically validated hazard-ratio estimator is not currently part of the production contract. Any future hazard-ratio implementation must be introduced as a separately versioned model with validation evidence and governance approval; it must not be inferred from the current Kaplan-Meier output.

## 4. Statistical guardrails

RiskIQ should not promote weak statistical associations to institutional decision logic.

The current governance policy for significance-oriented analysis is:

- minimum sample: n >= 12
- minimum absolute correlation: |r| >= 0.50
- statistical significance: p < 0.05

These are governance guardrails, not proof of causality. A relationship satisfying them must still be reviewed for sampling bias, leakage, confounding, temporal instability and business plausibility.

No causal claim may be generated merely from correlation.

## 5. AI immutability contract

The unified Risk Intelligence contract explicitly exposes:

ai_mutable_fields = []

The Copilot receives calculated evidence for interpretation. It does not receive an authorization contract allowing modification of:

- PAR values
- NPL
- exposure
- transition probabilities
- PD outputs
- survival curves
- stress outputs
- risk events
- decision outcomes
- policy versions

The risk-event grounding endpoint is explicitly read_only=true and ai_mutable_fields=[].

## 6. DSI evidence immutability

DSI reports use canonical JSON serialization:

- keys sorted;
- compact separators;
- deterministic string conversion for non-JSON-native values.

The SHA-256 digest is:

H = SHA256(CanonicalJSON(EvidencePayload))

The resulting evidence_hash is stored with the report.

Verification recalculates the canonical hash from the persisted evidence and compares it to the supplied digest. A mismatch sets tamper_detected=true.

When DSI_AUDIT_SIGNING_SECRET is configured, RiskIQ additionally computes:

Signature = HMAC-SHA256(secret, evidence_hash)

This provides authenticity in addition to integrity.

## 7. Governance principles

1. Deterministic engines are authoritative for quantitative facts.
2. AI may interpret but cannot mutate quantitative evidence.
3. Every production model/engine contract must be versioned.
4. Backtests and validation evidence must remain auditable.
5. Scenario stress is not represented as a forecast unless a governed predictive model exists.
6. Statistical significance does not establish causality.
7. DSI evidence must be reproducible from its canonical payload.
8. Third-party adapters remain outside the deterministic risk core.
