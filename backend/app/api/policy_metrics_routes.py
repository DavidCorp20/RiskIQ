from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/v1/decision-builder", tags=["policy-metrics"])

POSITIVE = {"REVIEW", "DECLINE", "BLOCK", "HIGH_RISK", "CRITICAL"}


def _bad(value: Any) -> bool | None:
    if value is None:
        return None
    v = str(value).strip().lower()
    if v in {"1", "true", "yes", "y", "bad", "default", "defaulted", "delinquent", "chargeoff", "charged_off"}:
        return True
    if v in {"0", "false", "no", "n", "good", "current", "paid", "performing", "non_default"}:
        return False
    return None


def _rate(n: int, d: int) -> float | None:
    return round(n / d, 6) if d else None


def _classification(rows: list[dict[str, Any]]) -> dict[str, Any]:
    labeled = []
    for row in rows:
        bad = row.get("bad")
        if bad is None:
            bad = _bad(row.get("outcome"))
        if bad is None:
            continue
        decision = str(row.get("policy_decision") or row.get("decision") or "").upper()
        positive = decision in POSITIVE
        labeled.append((bool(bad), positive))

    tp = sum(bad and positive for bad, positive in labeled)
    tn = sum((not bad) and (not positive) for bad, positive in labeled)
    fp = sum((not bad) and positive for bad, positive in labeled)
    fn = sum(bad and (not positive) for bad, positive in labeled)
    n = len(labeled)
    bad_n = tp + fn
    good_n = tn + fp
    precision = _rate(tp, tp + fp)
    recall = _rate(tp, bad_n)
    specificity = _rate(tn, good_n)
    fpr = _rate(fp, good_n)
    f1 = _rate(2 * tp, 2 * tp + fp + fn)
    accuracy = _rate(tp + tn, n)

    return {
        "labeled": n,
        "bad_rate": _rate(bad_n, n),
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "false_positive_rate": fpr,
        "f1": f1,
        "bad_capture": recall,
    }


@router.post("/backtest-metrics")
def backtest_metrics(payload: dict) -> dict:
    rows = payload.get("results") or payload.get("rows") or []
    if not isinstance(rows, list):
        raise HTTPException(status_code=422, detail=["results must be an array"])
    metrics = _classification(rows)
    return {
        "metrics": metrics,
        "validation_status": "VALIDATED" if metrics["labeled"] else "REPLAY_ONLY",
        "validation_message": (
            "Classification metrics are calculated only from rows with interpretable binary outcomes."
            if metrics["labeled"]
            else "No interpretable binary outcome labels were supplied; replay metrics are not predictive validation."
        ),
        "methodology": {
            "positive_decisions": sorted(POSITIVE),
            "note": "Historical replay without later outcomes is not causal evidence of policy performance.",
        },
    }
