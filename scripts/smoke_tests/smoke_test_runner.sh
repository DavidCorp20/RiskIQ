#!/usr/bin/env bash
set -euo pipefail

BASE_URL="\${RISKIQ_BASE_URL:-https://riskiq-api-v2-production.up.railway.app}"
DATASET_ID="\${RISKIQ_DATASET_ID:-}"
TMP_DIR="\${TMPDIR:-/tmp}/riskiq-smoke"
mkdir -p "$TMP_DIR"

if [[ -z "$DATASET_ID" ]]; then
  echo "ERROR: RISKIQ_DATASET_ID is required" >&2
  exit 2
fi

request() {
  local method="$1" url="$2" body="\${3:-}" output="$4"
  if [[ -n "$body" ]]; then
    curl --fail-with-body --silent --show-error --request "$method" \
      --header "Content-Type: application/json" \
      --data "$body" --output "$output" --write-out "%{http_code}" "$url"
  else
    curl --fail-with-body --silent --show-error --request "$method" \
      --output "$output" --write-out "%{http_code}" "$url"
  fi
}

assert_status() {
  local actual="$1" expected="$2" label="$3" file="$4"
  if [[ "$actual" != "$expected" ]]; then
    echo "FAIL: $label returned HTTP $actual (expected $expected)" >&2
    cat "$file" >&2 || true
    exit 1
  fi
  echo "PASS: $label -> HTTP $actual"
}

HEALTH="$TMP_DIR/health.json"
STATUS="$(request GET "$BASE_URL/health" "" "$HEALTH")"
assert_status "$STATUS" "200" "health" "$HEALTH"
python3 - "$HEALTH" <<'PY'
import json, sys
p=json.load(open(sys.argv[1]))
assert p.get("status")=="ok", p
PY

DSI="$TMP_DIR/dsi.json"
STATUS="$(request POST "$BASE_URL/api/v1/reports/dsi-export" \
  "{\"dataset_id\":\"$DATASET_ID\",\"scenario\":\"BASE\"}" "$DSI")"
assert_status "$STATUS" "200" "DSI export" "$DSI"
HASH="$(python3 - "$DSI" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))
assert p.get("evidence_hash"), p
print(p["evidence_hash"])
PY
)"

VERIFY="$TMP_DIR/verify.json"
STATUS="$(request GET "$BASE_URL/api/v1/reports/verify/$HASH" "" "$VERIFY")"
assert_status "$STATUS" "200" "DSI verify" "$VERIFY"
python3 - "$VERIFY" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))
assert p.get("verified") is True, p
assert p.get("tamper_detected") is False, p
PY

STRESS="$TMP_DIR/stress.json"
STATUS="$(request POST "$BASE_URL/api/v1/stress-testing/run" \
  '{"baseline":{"par30":0.10,"par60":0.05,"par90":0.03,"exposure":1000000},"profile":"LATAM_SEVERE_INFLATION","scenario":"SEVERE_STRESS"}' "$STRESS")"
assert_status "$STATUS" "200" "LATAM severe stress" "$STRESS"

INTELLIGENCE="$TMP_DIR/intelligence.json"
STATUS="$(request GET "$BASE_URL/api/v1/risk-intelligence/$DATASET_ID" "" "$INTELLIGENCE")"
assert_status "$STATUS" "200" "risk intelligence" "$INTELLIGENCE"
python3 - "$INTELLIGENCE" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))
assert p.get("deterministic") is True, p
assert p.get("ai_mutable_fields")==[], p
assert p.get("evidence_hash"), p
PY

echo "RiskIQ smoke suite PASSED"
echo "base_url=$BASE_URL"
echo "dataset_id=$DATASET_ID"
echo "evidence_hash=$HASH"
