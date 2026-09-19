from __future__ import annotations

from enum import Enum
from math import isfinite

from scipy.stats import pearsonr, spearmanr

from app.market.models import StatisticalEvidence


class CorrelationMethod(str, Enum):
    PEARSON = "pearson"
    SPEARMAN = "spearman"


class TimeSeriesStatistics:
    """Deterministic statistical layer. It never assigns causality."""

    def __init__(self, *, min_sample_size: int = 12, alpha: float = 0.05) -> None:
        if min_sample_size < 3:
            raise ValueError("min_sample_size must be >= 3")
        if not 0 < alpha < 1:
            raise ValueError("alpha must be between 0 and 1")
        self.min_sample_size = min_sample_size
        self.alpha = alpha

    def correlate(
        self,
        *,
        metric: str,
        market_indicator: str,
        x: list[float],
        y: list[float],
        method: CorrelationMethod = CorrelationMethod.PEARSON,
    ) -> StatisticalEvidence:
        if len(x) != len(y):
            raise ValueError("series must have equal length")

        finite_pairs = [
            (float(a), float(b))
            for a, b in zip(x, y)
            if isfinite(float(a)) and isfinite(float(b))
        ]
        n = len(finite_pairs)

        if n < self.min_sample_size:
            return StatisticalEvidence(
                metric=metric,
                market_indicator=market_indicator,
                sample_size=n,
                method=method.value,
                validated=False,
                validation_notes=f"Insufficient sample: n={n}; minimum required is {self.min_sample_size}.",
            )

        xs = [pair[0] for pair in finite_pairs]
        ys = [pair[1] for pair in finite_pairs]

        try:
            if method == CorrelationMethod.SPEARMAN:
                result = spearmanr(xs, ys)
            else:
                result = pearsonr(xs, ys)
            coefficient = float(result.statistic)
            p_value = float(result.pvalue)
        except (ValueError, FloatingPointError):
            return StatisticalEvidence(
                metric=metric,
                market_indicator=market_indicator,
                sample_size=n,
                method=method.value,
                validated=False,
                validation_notes="Correlation could not be computed for the supplied series.",
            )

        validated = (
            isfinite(coefficient)
            and isfinite(p_value)
            and -1.0 <= coefficient <= 1.0
            and abs(coefficient) >= 0.50
            and 0.0 <= p_value <= self.alpha
        )

        note = (
            f"n={n}, |r|={abs(coefficient):.4f}, p={p_value:.6g}, alpha={self.alpha}."
            if validated
            else f"n={n}, |r|={abs(coefficient):.4f}, p={p_value:.6g}; correlation threshold not met."
        )

        return StatisticalEvidence(
            metric=metric,
            market_indicator=market_indicator,
            coefficient=round(coefficient, 8),
            p_value=round(p_value, 8),
            sample_size=n,
            method=method.value,
            validated=validated,
            validation_notes=note,
        )

    @staticmethod
    def transform(values: list[float], transformation: str) -> list[float]:
        if transformation == "level":
            return [float(value) for value in values]

        if len(values) < 2:
            return []

        if transformation == "change":
            return [float(values[index] - values[index - 1]) for index in range(1, len(values))]

        if transformation in {"pct_change", "return"}:
            result: list[float] = []
            for index in range(1, len(values)):
                previous = float(values[index - 1])
                current = float(values[index])
                if previous == 0:
                    result.append(float("nan"))
                else:
                    result.append((current - previous) / abs(previous))
            return result

        raise ValueError(f"Unsupported transformation: {transformation}")
