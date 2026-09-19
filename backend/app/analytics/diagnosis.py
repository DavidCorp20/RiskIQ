from __future__ import annotations

from typing import Any


class DiagnosisService:
    """Turn deterministic portfolio analytics into an evidence-backed decision brief."""

    VERSION = "diagnosis-v1"

    def build(self, analysis: dict[str, Any], *, data_quality: dict[str, Any] | None = None, readiness: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        quality = data_quality or analysis.get("data_quality") or {}
        posture = analysis.get("posture") or {}
        materiality = analysis.get("materiality") or {}
        concentration = list(analysis.get("concentration") or [])
        priorities = list(analysis.get("priorities") or [])
        evidence: list[dict[str, Any]] = []

        shares = materiality.get("shares") or {}
        if shares.get("par30") is not None:
            evidence.append({"metric": "PAR30", "value": shares["par30"], "unit": "ratio", "source": "deterministic_risk_intelligence", "meaning": "Mora de 30+ ponderada por saldo."})
        if shares.get("par90") is not None:
            evidence.append({"metric": "PAR90", "value": shares["par90"], "unit": "ratio", "source": "deterministic_risk_intelligence", "meaning": "Mora severa de 90+ ponderada por saldo."})

        top = concentration[0] if concentration else None
        if top:
            evidence.append({"metric": "top_concentration", "value": top.get("name"), "unit": "segment", "source": "deterministic_concentration", "meaning": "Principal foco de materialidad y deterioro relativo."})
            evidence.append({"metric": "top_concentration_share", "value": top.get("exposure_share"), "unit": "ratio", "source": "deterministic_concentration", "meaning": "Participación de la exposición del foco principal."})

        limitations = []
        if quality.get("confidence"):
            limitations.append({"type": "data_confidence", "value": quality.get("confidence"), "message": quality.get("limitation") or "La confianza depende de cobertura y consistencia del dato."})
        if readiness:
            unavailable = [item.get("model") for item in readiness if not item.get("ready")]
            if unavailable:
                limitations.append({"type": "analysis_readiness", "value": unavailable, "message": "Hay metodologías que no deben ejecutarse hasta completar los campos requeridos."})

        next_best = self._next_best_analysis(analysis, readiness or [])
        decision_candidates = [
            {
                "title": item.get("title"),
                "type": item.get("type"),
                "priority": item.get("rank"),
                "evidence": item.get("evidence") or {},
                "human_review_required": True,
            }
            for item in priorities
        ]

        return {
            "version": self.VERSION,
            "status": posture.get("level") or "unknown",
            "headline": posture.get("label") or "Diagnóstico pendiente",
            "interpretation": analysis.get("interpretation") or "No existe interpretación determinística suficiente.",
            "materiality": materiality,
            "top_driver": self._driver(top),
            "evidence": evidence,
            "limitations": limitations,
            "next_best_analysis": next_best,
            "decision_candidates": decision_candidates[:6],
            "governance": {
                "evidence_backed": True,
                "causality_claimed": False,
                "automated_customer_action": False,
                "human_review_required": True,
            },
        }

    @staticmethod
    def _driver(item: dict[str, Any] | None) -> dict[str, Any]:
        if not item:
            return {"available": False, "message": "No hay una dimensión de concentración suficiente para aislar un driver principal."}
        return {
            "available": True,
            "name": item.get("name"),
            "exposure_share": item.get("exposure_share"),
            "par30": item.get("par30"),
            "bad30_contribution": item.get("contribution_to_portfolio_bad_30"),
            "priority_score": item.get("priority_score"),
            "risk_level": item.get("risk_level"),
        }

    @staticmethod
    def _next_best_analysis(analysis: dict[str, Any], readiness: list[dict[str, Any]]) -> dict[str, Any]:
        ready = {item.get("model") for item in readiness if item.get("ready")}
        if "Vintage Analysis" in ready:
            return {"model": "Vintage Analysis", "reason": "Permite comprobar si el deterioro está concentrado en cohortes de originación recientes o antiguas."}
        if "Concentration Analysis" in ready:
            return {"model": "Concentration Analysis", "reason": "Permite localizar materialidad y deterioro entre segmentos."}
        if "Migration / Roll Rate" in ready:
            return {"model": "Migration / Roll Rate", "reason": "Permite medir velocidad entre estados cuando existen snapshots comparables."}
        return {"model": "Delinquency Analysis", "reason": "Es el análisis base disponible para estructurar el deterioro por bandas de mora."}
