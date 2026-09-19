from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from math import isfinite
from typing import Iterable

from app.market.models import HistoricalSeries, TimeSeriesPoint


class SeriesFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class AlignmentPolicy:
    """Explicit temporal alignment contract for portfolio/market evidence."""

    def __init__(
        self,
        *,
        tolerance_days: int = 3,
        frequency: SeriesFrequency = SeriesFrequency.MONTHLY,
        prefer_previous: bool = True,
        exclude_weekends: bool = True,
    ) -> None:
        if tolerance_days < 0:
            raise ValueError("tolerance_days must be >= 0")
        self.tolerance_days = tolerance_days
        self.frequency = frequency
        self.prefer_previous = prefer_previous
        self.exclude_weekends = exclude_weekends

    def normalize(self, value: date) -> date:
        if self.frequency == SeriesFrequency.DAILY:
            return value
        if self.frequency == SeriesFrequency.WEEKLY:
            return value - timedelta(days=value.weekday())
        # Monthly alignment uses month-end. This prevents comparing different
        # calendar days inside a month and is deterministic across providers.
        if value.month == 12:
            next_month = date(value.year + 1, 1, 1)
        else:
            next_month = date(value.year, value.month + 1, 1)
        return next_month - timedelta(days=1)

    def candidate_dates(self, target: date) -> list[date]:
        normalized = self.normalize(target)
        candidates = [normalized + timedelta(days=offset) for offset in range(-self.tolerance_days, self.tolerance_days + 1)]
        if self.exclude_weekends:
            candidates = [item for item in candidates if item.weekday() < 5]
        return candidates


@dataclass(frozen=True)
class AlignedObservation:
    date: date
    portfolio_value: float
    market_value: float
    market_date: date
    distance_days: int


class TimeSeriesAligner:
    """Aligns two normalized historical series under an explicit policy."""

    def align(
        self,
        portfolio: HistoricalSeries,
        market: HistoricalSeries,
        policy: AlignmentPolicy | None = None,
    ) -> list[AlignedObservation]:
        policy = policy or AlignmentPolicy()
        portfolio_points = self._prepare(portfolio.points, policy)
        market_points = self._prepare(market.points, policy)
        market_by_date = {point.date: point for point in market_points}

        aligned: list[AlignedObservation] = []
        for portfolio_point in portfolio_points:
            target = policy.normalize(portfolio_point.date)
            candidates = []
            for candidate_date in policy.candidate_dates(target):
                point = market_by_date.get(candidate_date)
                if point is not None:
                    candidates.append(point)

            if not candidates:
                continue

            if policy.prefer_previous:
                previous = [p for p in candidates if p.date <= target]
                chosen = max(previous, key=lambda p: p.date) if previous else min(
                    candidates, key=lambda p: abs((p.date - target).days)
                )
            else:
                chosen = min(candidates, key=lambda p: abs((p.date - target).days))

            aligned.append(
                AlignedObservation(
                    date=portfolio_point.date,
                    portfolio_value=float(portfolio_point.value),
                    market_value=float(chosen.value),
                    market_date=chosen.date,
                    distance_days=abs((chosen.date - target).days),
                )
            )

        return aligned

    @staticmethod
    def _prepare(
        points: Iterable[TimeSeriesPoint],
        policy: AlignmentPolicy,
    ) -> list[TimeSeriesPoint]:
        prepared: dict[date, TimeSeriesPoint] = {}
        for point in points:
            if not isfinite(float(point.value)):
                continue
            normalized = policy.normalize(point.date)
            prepared[normalized] = TimeSeriesPoint(date=normalized, value=float(point.value))
        return sorted(prepared.values(), key=lambda item: item.date)
