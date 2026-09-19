from __future__ import annotations

from typing import Any

from app.market.models import (
    CorrelationFinding,
    EvidenceClassification,
    HistoricalSeries,
    StatisticalEvidence,
)
from app.market.statistics import CorrelationMethod, TimeSeriesStatistics
from app.market.timeseries import AlignmentPolicy, TimeSeriesAligner


class RiskMarketCorrelationEngine:
    """Deterministic market/portfolio evidence engine.

    OBSERVED -> CORRELATED is allowed only when the aligned sample meets
    minimum-n, coefficient and p-value requirements. Statistical evidence
    never upgrades a finding to causality.
    """

    def __init__(
        self,
        alpha: float = 0.05,
        min_sample_size: int = 12,
        aligner: TimeSeriesAligner | None = None,
    ) -> None:
        self.alpha = alpha
        self.min_sample_size = min_sample_size
        self.aligner = aligner or TimeSeriesAligner()
        self.statistics = TimeSeriesStatistics(
            min_sample_size=min_sample_size,
            alpha=alpha,
        )

    def analyze_series(
        self,
        *,
        portfolio: HistoricalSeries,
        market: HistoricalSeries,
        policy: AlignmentPolicy | None = None,
        portfolio_transformation: str = "level",
        market_transformation: str = "level",
        methods: list[CorrelationMethod] | None = None,
    ) -> list[StatisticalEvidence]:
        aligned = self.aligner.align(portfolio, market, policy)
        portfolio_values = [item.portfolio_value for item in aligned]
        market_values = [item.market_value for item in aligned]

        # Transformations are applied after alignment so both vectors retain
        # identical temporal support.
        portfolio_values = self.statistics.transform(
            portfolio_values, portfolio_transformation
        )
        market_values = self.statistics.transform(
            market_values, market_transformation
        )

        methods = methods or [
            CorrelationMethod.PEARSON,
            CorrelationMethod.SPEARMAN,
        ]

        return [
            self.statistics.correlate(
                metric=portfolio.name,
                market_indicator=market.name,
                x=portfolio_values,
                y=market_values,
                method=method,
            )
            for method in methods
        ]

    def classify(
        self,
        *,
        portfolio_observation: dict[str, Any],
        market_observation: dict[str, Any] | None = None,
        statistical_evidence: StatisticalEvidence | None = None,
        causal_evidence: dict[str, Any] | None = None,
    ) -> CorrelationFinding:
        if market_observation is None:
            return CorrelationFinding(
                classification=EvidenceClassification.OBSERVED,
                statement="Solo existe evidencia observada de cartera; no se recibió observación externa comparable.",
                portfolio_metric=str(portfolio_observation.get("metric") or ""),
            )

        # CAUSALITY_CONFIRMED is intentionally impossible without an explicit
        # externally validated causal-evidence contract. Correlation statistics
        # alone can never reach this branch.
        if causal_evidence and causal_evidence.get("validated") is True:
            return CorrelationFinding(
                classification=EvidenceClassification.CAUSALITY_CONFIRMED,
                statement="Existe evidencia causal formal marcada como validada por un proceso autorizado externo al motor de correlación.",
                portfolio_metric=str(portfolio_observation.get("metric") or ""),
                market_indicator=str(market_observation.get("symbol") or ""),
                statistical_evidence=statistical_evidence,
                causal_evidence=causal_evidence,
            )

        if statistical_evidence and self._is_valid_correlation(statistical_evidence):
            return CorrelationFinding(
                classification=EvidenceClassification.CORRELATED,
                statement="La serie de cartera y la serie externa presentan una relación estadística validada; esto no implica causalidad.",
                portfolio_metric=str(portfolio_observation.get("metric") or ""),
                market_indicator=str(market_observation.get("symbol") or ""),
                statistical_evidence=statistical_evidence,
            )

        return CorrelationFinding(
            classification=EvidenceClassification.POSSIBLE_EXPLANATION,
            statement="El movimiento externo puede utilizarse como contexto analítico, pero la evidencia no demuestra una correlación estadística válida ni causalidad.",
            portfolio_metric=str(portfolio_observation.get("metric") or ""),
            market_indicator=str(market_observation.get("symbol") or ""),
            statistical_evidence=statistical_evidence,
        )

    def transition_state(
        self,
        evidence: StatisticalEvidence | None,
        *,
        has_external_observation: bool,
    ) -> EvidenceClassification:
        """Return the only automatic statistical state transition.

        OBSERVED -> CORRELATED requires validated statistics. All other cases
        remain contextual/observed. CAUSALITY_CONFIRMED is never returned here.
        """
        if not has_external_observation:
            return EvidenceClassification.OBSERVED
        if evidence and self._is_valid_correlation(evidence):
            return EvidenceClassification.CORRELATED
        return EvidenceClassification.POSSIBLE_EXPLANATION

    def _is_valid_correlation(self, evidence: StatisticalEvidence) -> bool:
        if not evidence.validated:
            return False
        if evidence.coefficient is None or evidence.p_value is None:
            return False
        if evidence.sample_size is None or evidence.sample_size < self.min_sample_size:
            return False
        if not (-1.0 <= evidence.coefficient <= 1.0):
            return False
        return 0.0 <= evidence.p_value <= self.alpha
