from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .models import TransitionMatrix

STATES = ("current", "early_1_29", "early_30_59", "late_60_89", "hard_90_plus")


def bucket(dpd: float) -> str:
    if dpd < 1:
        return "current"
    if dpd < 30:
        return "early_1_29"
    if dpd < 60:
        return "early_30_59"
    if dpd < 90:
        return "late_60_89"
    return "hard_90_plus"


class TransitionEngine:
    """Deterministic roll-rate transition engine.

    The public contract remains list[dict] -> TransitionMatrix. Internally the
    expensive grouping/sorting work is vectorized with pandas/numpy so large
    portfolio snapshots do not spend most of their time in Python loops.
    """

    def build_matrix(self, rows: list[dict[str, Any]]) -> TransitionMatrix:
        if not rows:
            return self._empty_matrix()

        frame = pd.DataFrame(rows)
        loan_col = frame.get("loan_id")
        if loan_col is None:
            loan_col = frame.get("customer_id")
        if loan_col is None or "dpd" not in frame.columns:
            return self._empty_matrix()

        frame = frame.assign(
            _loan=loan_col.astype("string").fillna(""),
            _dpd=pd.to_numeric(frame["dpd"], errors="coerce").fillna(0.0),
            _snapshot=frame.get("snapshot_date", pd.Series(index=frame.index, dtype="string")).astype("string").fillna(""),
        )
        frame = frame.loc[frame["_loan"].ne("")].sort_values(["_loan", "_snapshot"], kind="mergesort")
        if frame.empty:
            return self._empty_matrix()

        dpd = frame["_dpd"].to_numpy(dtype=float, copy=False)
        states = np.select(
            [dpd < 1, dpd < 30, dpd < 60, dpd < 90],
            [STATES[0], STATES[1], STATES[2], STATES[3]],
            default=STATES[4],
        )
        frame["_state"] = states
        frame["_next_state"] = frame.groupby("_loan", sort=False)["_state"].shift(-1)
        transitions = frame.dropna(subset=["_next_state"])[["_state", "_next_state"]]

        counts = {state: {target: 0 for target in STATES} for state in STATES}
        if not transitions.empty:
            grouped = transitions.groupby(["_state", "_next_state"], sort=False).size()
            for (source, target), value in grouped.items():
                if source in counts and target in counts[source]:
                    counts[source][target] = int(value)

        probabilities: dict[str, dict[str, float]] = {}
        for source in STATES:
            total = sum(counts[source].values())
            probabilities[source] = {
                target: (counts[source][target] / total if total else (1.0 if source == target else 0.0))
                for target in STATES
            }

        return TransitionMatrix(
            states=list(STATES),
            probabilities=probabilities,
            counts=counts,
            sample_size=int(len(transitions)),
            methodology="observed-roll-rate-transition-matrix-v2-vectorized",
        )

    def project_pd(self, matrix: TransitionMatrix, horizon_periods: int = 1) -> dict[str, float]:
        if horizon_periods < 1:
            raise ValueError("horizon_periods must be >= 1")
        m = np.asarray(
            [[matrix.probabilities[s][t] for t in matrix.states] for s in matrix.states],
            dtype=float,
        )
        p = np.linalg.matrix_power(m, horizon_periods)
        hard = matrix.states.index("hard_90_plus")
        return {matrix.states[i]: round(float(p[i, hard]), 8) for i in range(len(matrix.states))}

    @staticmethod
    def _empty_matrix() -> TransitionMatrix:
        probabilities = {
            state: {target: (1.0 if state == target else 0.0) for target in STATES}
            for state in STATES
        }
        counts = {state: {target: 0 for target in STATES} for state in STATES}
        return TransitionMatrix(
            states=list(STATES),
            probabilities=probabilities,
            counts=counts,
            sample_size=0,
            methodology="observed-roll-rate-transition-matrix-v2-vectorized",
        )
