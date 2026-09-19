from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.analytics.ews_models import (
    EWSFeatureSet,
    EWSResult,
    EWSSignal,
    SnapshotObservation,
)


class EWSEngine:
    """Low-latency deterministic Early Warning System calculator.

    The engine never calls an LLM and never labels its score as probability.
    It only converts observed longitudinal portfolio behaviour into a
    prioritization score from 0 to 100.
    """

    BUCKETS = (
        ("current", 0, 1),
        ("early_1_29", 1, 30),
        ("early_30_59", 30, 60),
        ("late_60_89", 60, 90),
        ("hard_90_plus", 90, None),
    )

    def __init__(
        self,
        *,
        dpd_delta_weight: float = 0.20,
        acceleration_weight: float = 0.20,
        severity_weight: float = 0.25,
        migration_weight: float = 0.15,
        pd_change_weight: float = 0.10,
        balance_weight: float = 0.10,
    ) -> None:
        weights = (
            dpd_delta_weight,
            acceleration_weight,
            severity_weight,
            migration_weight,
            pd_change_weight,
            balance_weight,
        )
        if abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError("EWS weights must sum to 1.0")
        self.weights = weights

    def calculate(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        observations = [SnapshotObservation.from_row(row) for row in rows]
        histories: dict[str, list[SnapshotObservation]] = defaultdict(list)
        for observation in observations:
            histories[observation.loan_id].append(observation)

        results = []
        for loan_id, history in histories.items():
            results.append(self.calculate_loan(history).to_dict())

        return sorted(results, key=lambda item: item["score"], reverse=True)

    def calculate_loan(self, history: list[SnapshotObservation]) -> EWSResult:
        if not history:
            raise ValueError("history cannot be empty")

        ordered = sorted(history, key=lambda item: item.snapshot_date)
        current = ordered[-1]
        previous = ordered[-2] if len(ordered) >= 2 else None
        previous_previous = ordered[-3] if len(ordered) >= 3 else None

        current_dpd = current.dpd
        previous_dpd = previous.dpd if previous else None
        dpd_delta = current.dpd - previous.dpd if previous else None
        prior_delta = (
            previous.dpd - previous_previous.dpd
            if previous and previous_previous
            else None
        )
        acceleration = dpd_delta - prior_delta if dpd_delta is not None and prior_delta is not None else None

        balance_delta = (
            current.outstanding_principal - previous.outstanding_principal
            if previous
            else None
        )
        pd_delta = current.pd - previous.pd if current.pd is not None and previous and previous.pd is not None else None

        max_dpd = max(item.dpd for item in ordered[-3:])
        bucket_from = self._bucket(previous.dpd) if previous else None
        bucket_to = self._bucket(current.dpd)
        observed_roll_rate = self._observed_roll_rate(ordered)

        features = EWSFeatureSet(
            loan_id=current.loan_id,
            snapshot_date=current.snapshot_date,
            current_dpd=current_dpd,
            previous_dpd=previous_dpd,
            dpd_delta=dpd_delta,
            dpd_acceleration=acceleration,
            max_dpd_lookback=max_dpd,
            current_balance=current.outstanding_principal,
            balance_delta=balance_delta,
            bucket_from=bucket_from,
            bucket_to=bucket_to,
            observed_roll_rate=observed_roll_rate,
            pd_delta=pd_delta,
            data_points=len(ordered),
            segment=current.segment,
            product_id=current.product_id,
        )

        signals: list[EWSSignal] = []

        severity_points = self._severity_points(current_dpd)
        if severity_points:
            signals.append(EWSSignal(
                code="DPD_SEVERITY",
                severity=self._severity(current_dpd),
                points=severity_points * self.weights[2],
                value=current_dpd,
                explanation=f"DPD actual de {current_dpd:.0f} días.",
            ))

        delta_points = self._delta_points(dpd_delta)
        if delta_points:
            signals.append(EWSSignal(
                code="DPD_DETERIORATION",
                severity="high" if (dpd_delta or 0) >= 15 else "medium",
                points=delta_points * self.weights[0],
                value=dpd_delta,
                explanation=f"El DPD aumentó {dpd_delta:.0f} días frente al snapshot anterior.",
            ))

        acceleration_points = self._acceleration_points(acceleration)
        if acceleration_points:
            signals.append(EWSSignal(
                code="DPD_ACCELERATION",
                severity="high" if (acceleration or 0) >= 10 else "medium",
                points=acceleration_points * self.weights[1],
                value=acceleration,
                explanation="La velocidad de deterioro del DPD está aumentando.",
            ))

        migration_points = self._migration_points(bucket_from, bucket_to)
        if migration_points:
            signals.append(EWSSignal(
                code="BUCKET_MIGRATION",
                severity="high" if migration_points >= 70 else "medium",
                points=migration_points * self.weights[3],
                value=f"{bucket_from}->{bucket_to}",
                explanation=f"Migración observada de {bucket_from} a {bucket_to}.",
            ))

        pd_points = self._pd_points(pd_delta)
        if pd_points:
            signals.append(EWSSignal(
                code="PD_DETERIORATION",
                severity="high" if (pd_delta or 0) >= 0.10 else "medium",
                points=pd_points * self.weights[4],
                value=pd_delta,
                explanation="La PD observada en el dataset aumentó frente al período anterior.",
            ))

        balance_points = self._balance_points(current.outstanding_principal, balance_delta)
        if balance_points:
            signals.append(EWSSignal(
                code="EXPOSURE_MATERIAL",
                severity="medium",
                points=balance_points * self.weights[5],
                value=current.outstanding_principal,
                explanation="Existe exposición positiva asociada a la trayectoria observada.",
            ))

        score = round(min(sum(signal.points for signal in signals), 100.0), 2)
        band = self._band(score)

        return EWSResult(
            loan_id=current.loan_id,
            snapshot_date=current.snapshot_date,
            score=score,
            band=band,
            signals=tuple(signals),
            features=features,
        )

    @classmethod
    def _bucket(cls, dpd: float) -> str:
        for name, lower, upper in cls.BUCKETS:
            if dpd >= lower and (upper is None or dpd < upper):
                return name
        return "hard_90_plus"

    @staticmethod
    def _severity_points(dpd: float) -> float:
        if dpd >= 90:
            return 100.0
        if dpd >= 60:
            return 80.0
        if dpd >= 30:
            return 60.0
        if dpd >= 8:
            return 35.0
        if dpd >= 1:
            return 15.0
        return 0.0

    @staticmethod
    def _severity(dpd: float) -> str:
        if dpd >= 90:
            return "critical"
        if dpd >= 60:
            return "high"
        if dpd >= 30:
            return "medium"
        return "low"

    @staticmethod
    def _delta_points(delta: float | None) -> float:
        if delta is None or delta <= 0:
            return 0.0
        return min(delta / 30.0 * 100.0, 100.0)

    @staticmethod
    def _acceleration_points(acceleration: float | None) -> float:
        if acceleration is None or acceleration <= 0:
            return 0.0
        return min(acceleration / 30.0 * 100.0, 100.0)

    @staticmethod
    def _pd_points(delta: float | None) -> float:
        if delta is None or delta <= 0:
            return 0.0
        return min(delta / 0.30 * 100.0, 100.0)

    @staticmethod
    def _balance_points(balance: float, delta: float | None) -> float:
        if balance <= 0:
            return 0.0
        # Exposure is a prioritization amplifier, not a probability signal.
        if delta is not None and delta < 0:
            return 35.0
        return 50.0

    @staticmethod
    def _migration_points(source: str | None, target: str) -> float:
        if source is None:
            return 0.0
        order = {
            "current": 0,
            "early_1_29": 1,
            "early_30_59": 2,
            "late_60_89": 3,
            "hard_90_plus": 4,
        }
        movement = order[target] - order[source]
        if movement <= 0:
            return 0.0
        return min(25.0 * movement, 100.0)

    @staticmethod
    def _observed_roll_rate(history: list[SnapshotObservation]) -> float | None:
        if len(history) < 2:
            return None
        previous = history[-2]
        current = history[-1]
        source = EWSEngine._bucket(previous.dpd)
        target = EWSEngine._bucket(current.dpd)
        if source == target:
            return 0.0
        return 1.0

    @staticmethod
    def _band(score: float) -> str:
        if score >= 75:
            return "critical"
        if score >= 50:
            return "high"
        if score >= 25:
            return "watch"
        return "normal"
