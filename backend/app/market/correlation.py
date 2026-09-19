from __future__ import annotations

from typing import Any

from app.market.models import (
    CorrelationFinding,
    EvidenceClassification,
    StatisticalEvidence,
)


class RiskMarketCorrelationEngine:
    """Strict evidence classifier.

    It deliberately refuses to label temporal coincidence as correlation and
    refuses to label correlation as causality. Formal causal evidence must be
    supplied by a validated external/statistical process.
    """

    def __init__(self, alpha: float = 0.05, min_sample_size: int = 30) -> None:
        self.alpha = alpha
        self.min_sample_size = min_sample_size

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

        if causal_evidence and causal_evidence.get("validated") is True:
            return CorrelationFinding(
                classification=EvidenceClassification.CAUSALITY_CONFIRMED,
                statement="Existe evidencia causal formal marcada como validada por el proceso estadístico autorizado.",
                portfolio_metric=str(portfolio_observation.get("metric") or ""),
                market_indicator=str(market_observation.get("symbol") or ""),
                statistical_evidence=statistical_evidence,
                causal_evidence=causal_evidence,
            )

        if statistical_evidence and self._is_valid_correlation(statistical_evidence):
            return CorrelationFinding(
                classification=EvidenceClassification.CORRELATED,
                statement="La serie de cartera y la serie externa presentan una relación estadística validada bajo el contrato recibido; esto no implica causalidad.",
                portfolio_metric=str(portfolio_observation.get("metric") or ""),
                market_indicator=str(market_observation.get("symbol") or ""),
                statistical_evidence=statistical_evidence,
            )

        return CorrelationFinding(
            classification=EvidenceClassification.POSSIBLE_EXPLANATION,
            statement="El movimiento externo puede utilizarse como contexto analítico, pero la evidencia recibida no demuestra una correlación estadística ni causalidad.",
            portfolio_metric=str(portfolio_observation.get("metric") or ""),
            market_indicator=str(market_observation.get("symbol") or ""),
            statistical_evidence=statistical_evidence,
        )

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
