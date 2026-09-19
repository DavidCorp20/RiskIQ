#!/usr/bin/env python3
"""Smoke test for RiskIQ Copilot Market Context.

Usage:
  python scripts/test_market_context.py --base-url https://riskiq-api-v2-production.up.railway.app --dataset-id DATASET_ID

The script validates:
- analytical questions request market context;
- NQ futures is NQ=F when market context is available;
- market_context_used is true when the provider returns available/partial data;
- deterministic PAR30/PAR60/exposure values are preserved;
- conversational greetings do not request market context.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import httpx


EXPECTED = {
    "par30": 0.1623,
    "par60": 0.0856,
    "exposure": 282670.0,
}


def close(a: Any, b: float, tolerance: float = 1e-6) -> bool:
    try:
        return abs(float(a) - b) <= tolerance
    except (TypeError, ValueError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--dataset-id", required=True)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    url = f"{base}/api/v1/ai/copilot"

    with httpx.Client(timeout=45) as client:
        analytical = client.post(
            url,
            json={
                "dataset_id": args.dataset_id,
                "question": "Analiza la cartera y relaciona PAR30, PAR60 y NPL con el contexto de mercado actual.",
                "conversation": [],
            },
        )
        analytical.raise_for_status()
        analytical_body = analytical.json()

        evidence = analytical_body.get("cro_evidence") or {}
        par = evidence.get("par") or {}
        exposure = evidence.get("exposure") or {}
        market = analytical_body.get("market_context") or {}
        nq = (market.get("data") or {}).get("nq_futures") or {}

        assert close((par.get("par30") or {}).get("ratio"), EXPECTED["par30"]), analytical_body
        assert close((par.get("par60") or {}).get("ratio"), EXPECTED["par60"]), analytical_body
        assert close(exposure.get("total_balance"), EXPECTED["exposure"]), analytical_body

        assert nq.get("symbol") == "NQ=F", {
            "market_context": market,
            "response": analytical_body,
        }
        assert analytical_body.get("market_context_used") is True, analytical_body

        greeting = client.post(
            url,
            json={
                "dataset_id": args.dataset_id,
                "question": "Hola",
                "conversation": [],
            },
        )
        greeting.raise_for_status()
        greeting_body = greeting.json()

        assert greeting_body.get("conversation_mode") == "conversational", greeting_body
        assert greeting_body.get("market_context", {}).get("status") == "not_requested", greeting_body
        assert greeting_body.get("market_context_used") is False, greeting_body

    print(json.dumps({
        "ok": True,
        "analytical": {
            "market_context_used": analytical_body.get("market_context_used"),
            "nq_symbol": nq.get("symbol"),
            "par30": (par.get("par30") or {}).get("ratio"),
            "par60": (par.get("par60") or {}).get("ratio"),
            "exposure": exposure.get("total_balance"),
        },
        "conversational": {
            "conversation_mode": greeting_body.get("conversation_mode"),
            "market_context_status": greeting_body.get("market_context", {}).get("status"),
            "market_context_used": greeting_body.get("market_context_used"),
        },
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
