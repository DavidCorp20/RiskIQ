from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SnapshotObservation:
    """Canonical point-in-time observation used by the deterministic EWS engine."""

    loan_id: str
    snapshot_date: str
    dpd: float = 0.0
    outstanding_principal: float = 0.0
    status: str | None = None
    pd: float | None = None
    lgd: float | None = None
    ead: float | None = None
    segment: str | None = None
    product_id: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "SnapshotObservation":
        def number(value: Any, default: float = 0.0) -> float:
            try:
                return float(value) if value not in (None, "") else default
            except (TypeError, ValueError):
                return default

        loan_id = str(row.get("loan_id") or row.get("id") or "").strip()
        if not loan_id:
            raise ValueError("loan_id is required for EWS observations")

        snapshot_date = str(
            row.get("snapshot_date")
            or row.get("snapshot_month")
            or row.get("as_of_date")
            or ""
        )[:10]
        if not snapshot_date:
            raise ValueError("snapshot_date is required for EWS observations")

        return cls(
            loan_id=loan_id,
            snapshot_date=snapshot_date,
            dpd=max(number(row.get("dpd")), 0.0),
            outstanding_principal=max(number(row.get("outstanding_principal")), 0.0),
            status=str(row["status"]) if row.get("status") not in (None, "") else None,
            pd=number(row.get("pd"), None) if row.get("pd") not in (None, "") else None,
            lgd=number(row.get("lgd"), None) if row.get("lgd") not in (None, "") else None,
            ead=number(row.get("ead"), None) if row.get("ead") not in (None, "") else None,
            segment=str(row["segment"]) if row.get("segment") not in (None, "") else None,
            product_id=str(row["product_id"]) if row.get("product_id") not in (None, "") else None,
        )


@dataclass(frozen=True)
class EWSFeatureSet:
    """Observed trajectory features. None means the history is insufficient."""

    loan_id: str
    snapshot_date: str
    current_dpd: float
    previous_dpd: float | None
    dpd_delta: float | None
    dpd_acceleration: float | None
    max_dpd_lookback: float
    current_balance: float
    balance_delta: float | None
    bucket_from: str | None
    bucket_to: str
    observed_roll_rate: float | None
    pd_delta: float | None
    data_points: int
    segment: str | None = None
    product_id: str | None = None


@dataclass(frozen=True)
class EWSSignal:
    code: str
    severity: str
    points: float
    value: float | str | None
    explanation: str


@dataclass(frozen=True)
class EWSResult:
    """Deterministic early-warning result; score is a prioritization score, not PD."""

    loan_id: str
    snapshot_date: str
    score: float
    band: str
    signals: tuple[EWSSignal, ...] = field(default_factory=tuple)
    features: EWSFeatureSet | None = None
    methodology: str = "deterministic-observed-trajectory-v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "loan_id": self.loan_id,
            "snapshot_date": self.snapshot_date,
            "score": self.score,
            "band": self.band,
            "signals": [
                {
                    "code": signal.code,
                    "severity": signal.severity,
                    "points": signal.points,
                    "value": signal.value,
                    "explanation": signal.explanation,
                }
                for signal in self.signals
            ],
            "features": self.features.__dict__ if self.features else None,
            "methodology": self.methodology,
            "predictive_probability": False,
        }
