from __future__ import annotations

import asyncio
import json
from hashlib import sha256
from typing import Any

from app.analytics.risk_analytics import RiskAnalyticsService
from app.data.persistence import PortfolioPersistenceService
from app.market.service import MarketContextService
from app.predictive.transition_engine import TransitionEngine
from app.predictive.pd_engine import PDEngine
from app.predictive.survival_engine import SurvivalEngine
from app.risk_events.repository import RiskActionRepository, RiskEventRepository
from app.stress_testing.stress_engine import StressEngine


class RiskIntelligenceProvider:
    """Single deterministic evidence contract for executive/Copilot consumers.

    Results are cached by dataset + snapshot token. The cache is invalidated when
    the dataset metadata timestamp changes or an explicit snapshot_id changes.
    AI cannot mutate any calculated field.
    """

    MAX_ROWS = 500_000
    CACHE_TTL_SECONDS = 60

    def __init__(self):
        self.persistence = PortfolioPersistenceService()
        self.analytics = RiskAnalyticsService()
        self.market = MarketContextService()
        self.events = RiskEventRepository()
        self.actions = RiskActionRepository()
        self.transition = TransitionEngine()
        self.pd = PDEngine()
        self.survival = SurvivalEngine()
        self.stress = StressEngine()
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    def _snapshot_token(self, dataset_id: str, snapshot_id: str | None) -> str:
        if snapshot_id:
            return str(snapshot_id)
        rows = self.persistence.datasets.find({"dataset_id": dataset_id}, limit=1)
        if rows:
            row = rows[0]
            return str(row.get("updated_at") or row.get("snapshot_id") or "")
        return ""

    async def build(
        self,
        dataset_id: str,
        rows: list[dict[str, Any]] | None = None,
        snapshot_id: str | None = None,
    ) -> dict[str, Any]:
        if not dataset_id:
            raise ValueError("dataset_id is required")

        token = self._snapshot_token(dataset_id, snapshot_id)
        cache_key = f"{dataset_id}:{token}"
        now = asyncio.get_running_loop().time()
        cached = self._cache.get(cache_key)
        if rows is None and cached and now - cached[0] < self.CACHE_TTL_SECONDS:
            result = dict(cached[1])
            result["cache"] = "hit"
            return result

        async with self._lock:
            now = asyncio.get_running_loop().time()
            cached = self._cache.get(cache_key)
            if rows is None and cached and now - cached[0] < self.CACHE_TTL_SECONDS:
                result = dict(cached[1])
                result["cache"] = "hit"
                return result

            rows = rows if rows is not None else self.persistence.portfolio_records.find(
                {"dataset_id": dataset_id},
                limit=self.MAX_ROWS,
            )
            if not rows:
                raise ValueError("Dataset has no portfolio records")
            if len(rows) > self.MAX_ROWS:
                raise ValueError(f"Dataset exceeds Risk Intelligence limit of {self.MAX_ROWS:,} rows")

            risk = self.analytics.analyze(rows)
            market = await self.market.get_context()
            events = self.events.list(dataset_id=dataset_id, limit=500)
            actions = self.actions.list(limit=500)
            dataset_actions = [
                a for a in actions if any(e.get("event_id") == a.get("event_id") for e in events)
            ]
            matrix = self.transition.build_matrix(rows)
            ratings = self.pd.ratings(matrix, 1)
            survival_rows = [r for r in rows if r.get("duration") is not None]
            survival = self.survival.kaplan_meier(survival_rows) if survival_rows else {
                "points": [], "methodology": "kaplan-meier-v2-vectorized", "sample_size": 0
            }
            payload = {
                "contract_version": "risk-intelligence-v1",
                "dataset_id": dataset_id,
                "snapshot_id": snapshot_id or token or None,
                "deterministic": True,
                "ai_mutable_fields": [],
                "portfolio": {"analytics": risk, "npl": self._npl(risk)},
                "market": market,
                "risk_events": {"events": events, "actions": dataset_actions},
                "predictive": {
                    "transition_matrix": matrix.model_dump(),
                    "pd_ratings": [x.model_dump() for x in ratings],
                    "survival": survival.model_dump() if hasattr(survival, "model_dump") else survival,
                },
                "stress_testing": {
                    "available": True,
                    "baseline": self._baseline(risk),
                    "scenarios": ["BASE", "ADVERSE", "SEVERE_STRESS"],
                    "projection_requires_validated_sensitivities": True,
                },
            }
            payload["evidence_hash"] = sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
            ).hexdigest()
            payload["cache"] = "miss"
            self._cache[cache_key] = (now, dict(payload))
            return payload

    @staticmethod
    def _baseline(risk):
        par = risk.get("par") or {}
        return {
            "par30": float((par.get("par30") or {}).get("ratio", 0)),
            "par60": float((par.get("par60") or {}).get("ratio", 0)),
            "par90": float((par.get("par90") or {}).get("ratio", 0)),
            "exposure": float(risk.get("exposure", 0)),
        }

    @staticmethod
    def _npl(risk):
        return risk.get("npl") or None
