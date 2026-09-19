from __future__ import annotations

from typing import Any

import numpy as np

from .models import SurvivalCurve, SurvivalPoint


class SurvivalEngine:
    """Deterministic Kaplan-Meier estimator using vectorized numpy operations."""

    def kaplan_meier(
        self,
        rows: list[dict[str, Any]],
        event_field: str = "default",
        duration_field: str = "duration",
    ) -> SurvivalCurve:
        durations: list[int] = []
        events: list[int] = []
        positive_events = {"1", "true", "yes", "bad", "default", "defaulted"}

        for row in rows:
            value = row.get(duration_field)
            if value is None:
                continue
            try:
                duration = max(0, int(float(value)))
            except (TypeError, ValueError):
                continue
            raw = row.get(event_field, False)
            event = 1 if str(raw).lower() in positive_events else 0
            durations.append(duration)
            events.append(event)

        if not durations:
            return SurvivalCurve(points=[], methodology="kaplan-meier-v2-vectorized", sample_size=0)

        d = np.asarray(durations, dtype=np.int64)
        e = np.asarray(events, dtype=np.int8)
        periods, inverse = np.unique(d, return_inverse=True)
        counts_at_period = np.bincount(inverse, minlength=len(periods))
        events_at_period = np.bincount(inverse, weights=e, minlength=len(periods)).astype(np.int64)
        at_risk = np.cumsum(counts_at_period[::-1])[::-1]
        survival = np.cumprod(1.0 - np.divide(
            events_at_period,
            at_risk,
            out=np.zeros_like(events_at_period, dtype=float),
            where=at_risk > 0,
        ))

        points = [
            SurvivalPoint(
                period=int(period),
                at_risk=int(risk),
                events=int(event_count),
                survival=round(float(surv), 8),
            )
            for period, risk, event_count, surv in zip(periods, at_risk, events_at_period, survival)
        ]
        return SurvivalCurve(
            points=points,
            methodology="kaplan-meier-v2-vectorized",
            sample_size=len(durations),
        )
