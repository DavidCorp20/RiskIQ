from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any

import numpy as np
from scipy.stats import ks_2samp


@dataclass(frozen=True)
class ValidationResult:
    model_id: str
    model_version: str
    validation_window: str
    metrics: dict[str, Any]
    thresholds: dict[str, float]
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": "risk-intelligence-v1",
            "model_id": self.model_id,
            "model_version": self.model_version,
            "validation_window": self.validation_window,
            "metrics": self.metrics,
            "thresholds": self.thresholds,
            "status": self.status,
            "methodology": "deterministic-model-validation-v1",
        }


def _validate_binary(scores: list[float], labels: list[int]) -> tuple[np.ndarray, np.ndarray]:
    if len(scores) != len(labels) or len(scores) < 2:
        raise ValueError("scores and labels must have equal length >= 2")
    y = np.asarray(labels, dtype=int)
    if not set(y.tolist()).issubset({0, 1}) or len(set(y.tolist())) < 2:
        raise ValueError("labels must contain both 0 and 1")
    p = np.asarray(scores, dtype=float)
    if not np.isfinite(p).all():
        raise ValueError("scores must be finite")
    return p, y


def auc_gini_ks(scores: list[float], labels: list[int]) -> dict[str, float]:
    p, y = _validate_binary(scores, labels)
    order = np.argsort(p, kind="mergesort")
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(p) + 1)
    positives = float(y.sum())
    negatives = float(len(y) - y.sum())
    rank_sum = float(ranks[y == 1].sum())
    auc = (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)
    thresholds = np.sort(np.unique(p))[::-1]
    ks = 0.0
    for threshold in thresholds:
        pred = p >= threshold
        tpr = float((pred & (y == 1)).sum()) / positives
        fpr = float((pred & (y == 0)).sum()) / negatives
        ks = max(ks, abs(tpr - fpr))
    return {"auc": float(auc), "gini": float(2 * auc - 1), "ks": float(ks)}


def brier_score(scores: list[float], labels: list[int]) -> float:
    p, y = _validate_binary(scores, labels)
    return float(np.mean((p - y) ** 2))


def calibration_curve(scores: list[float], labels: list[int], bins: int = 10) -> list[dict[str, float | int]]:
    p, y = _validate_binary(scores, labels)
    edges = np.linspace(0.0, 1.0, bins + 1)
    result: list[dict[str, float | int]] = []
    for i in range(bins):
        mask = (p >= edges[i]) & (p <= edges[i + 1] if i == bins - 1 else p < edges[i + 1])
        if not mask.any():
            continue
        result.append({
            "bin": i,
            "count": int(mask.sum()),
            "predicted": float(p[mask].mean()),
            "observed": float(y[mask].mean()),
        })
    return result


def psi(expected: list[float], actual: list[float], bins: int = 10) -> float:
    e = np.asarray(expected, dtype=float)
    a = np.asarray(actual, dtype=float)
    if len(e) < 2 or len(a) < 2:
        raise ValueError("PSI requires two non-empty populations")
    if not np.isfinite(e).all() or not np.isfinite(a).all():
        raise ValueError("PSI populations must be finite")
    edges = np.unique(np.quantile(e, np.linspace(0, 1, bins + 1)))
    if len(edges) < 2:
        return 0.0
    ep, _ = np.histogram(e, bins=edges)
    ap, _ = np.histogram(a, bins=edges)
    ep = np.clip(ep / len(e), 1e-6, None)
    ap = np.clip(ap / len(a), 1e-6, None)
    return float(np.sum((ap - ep) * np.log(ap / ep)))


def csi(expected: list[float], actual: list[float], bins: int = 10) -> float:
    return psi(expected, actual, bins=bins)


def stability(expected: list[float], actual: list[float]) -> dict[str, float]:
    e = np.asarray(expected, dtype=float)
    a = np.asarray(actual, dtype=float)
    if len(e) < 2 or len(a) < 2:
        raise ValueError("stability requires two populations")
    ks_stat = float(ks_2samp(e, a).statistic)
    return {"psi": psi(expected, actual), "ks_drift": ks_stat, "csi": csi(expected, actual)}


def validate_model(
    *,
    model_id: str,
    model_version: str,
    validation_window: str,
    scores: list[float],
    labels: list[int],
    expected_population: list[float] | None = None,
    actual_population: list[float] | None = None,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    metrics = auc_gini_ks(scores, labels)
    metrics["brier"] = brier_score(scores, labels)
    metrics["calibration_curve"] = calibration_curve(scores, labels)
    if expected_population is not None and actual_population is not None:
        metrics["stability"] = stability(expected_population, actual_population)
    thresholds = thresholds or {
        "auc_min": 0.60,
        "gini_min": 0.20,
        "ks_min": 0.20,
        "brier_max": 0.25,
        "psi_warning": 0.10,
        "psi_fail": 0.25,
    }
    failures = [
        metrics["auc"] < thresholds["auc_min"],
        metrics["gini"] < thresholds["gini_min"],
        metrics["ks"] < thresholds["ks_min"],
        metrics["brier"] > thresholds["brier_max"],
    ]
    psi_value = metrics.get("stability", {}).get("psi")
    if psi_value is not None and psi_value >= thresholds["psi_fail"]:
        failures.append(True)
    warnings = [
        psi_value is not None and psi_value >= thresholds["psi_warning"],
    ]
    status = "FAIL" if any(failures) else ("WARNING" if any(warnings) else "PASS")
    return ValidationResult(
        model_id=model_id,
        model_version=model_version,
        validation_window=validation_window,
        metrics=metrics,
        thresholds=thresholds,
        status=status,
    ).to_dict()
