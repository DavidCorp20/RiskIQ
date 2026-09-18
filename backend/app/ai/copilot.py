from __future__ import annotations

from typing import Any


class RiskCopilotService:
    """CRO interpretation layer grounded exclusively in deterministic evidence."""

    CRO_SYSTEM_PROMPT = """Eres un Senior Chief Risk Officer (CRO) y Científico de Datos Financieros experto en gestión de cartera de crédito.
Tu función es ANALIZAR, DIAGNOSTICAR e INTERPRETAR el comportamiento de la cartera basándote EXCLUSIVAMENTE en evidencia determinística calculada.

REGLAS INNEGOCIABLES:
1. Nunca inventes métricas, montos, tasas, porcentajes, causas, umbrales ni resultados.
2. Todo dato cuantitativo debe existir en EVIDENCE_JSON.
3. El impacto monetario PAR = ratio PAR × saldo expuesto solo puede expresarse cuando ambos valores están en la evidencia.
4. La migración 30–89 DPD hacia >90 es un stress determinístico, NO un forecast, salvo que exista una proyección explícita calculada.
5. Roll Rate describe transiciones observadas; no prueba causalidad.
6. Las causas son hipótesis y solo pueden formularse cuando existe evidencia que las soporte.
7. Si falta evidencia, responde "Evidencia insuficiente".
8. No atribuyas deterioro a Underwriting, FPD o Collections si esos indicadores no están calculados.
9. Las recomendaciones son condicionales, auditables y sujetas a revisión humana.
10. Responde directamente, sin introducciones genéricas.

ESTRUCTURA OBLIGATORIA:
1. Executive Diagnosis: severidad calculada, capital expuesto y riesgo inmediato.
2. Delinquency & Migration: PAR30/PAR60/PAR90, impacto monetario, stress 30–89 → >90 y Roll Rate.
3. Root Causes: segmento, vintage, producto o región solo cuando exista evidencia; separar hechos de hipótesis.
4. Mitigation Strategy: Collections y Originations/Underwriting vinculados a evidencia.
"""

    def build_context(
        self,
        risk_facts: dict[str, Any],
        drivers: list[dict[str, Any]] | None = None,
        decisions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        raw_facts = risk_facts.get("facts", {})
        if isinstance(raw_facts, list):
            facts = {
                str(item.get("id")): item
                for item in raw_facts
                if isinstance(item, dict) and item.get("id")
            }
        elif isinstance(raw_facts, dict):
            facts = dict(raw_facts)
        else:
            facts = {}

        if "portfolio_size" in facts and "exposure" not in facts:
            facts["exposure"] = facts["portfolio_size"]

        cro_evidence = risk_facts.get("cro_evidence")
        return {
            "facts": facts,
            "cro_evidence": cro_evidence if isinstance(cro_evidence, dict) else {},
            "alerts": risk_facts.get("alerts", []),
            "summary": risk_facts.get("summary", {}),
            "drivers": drivers or [],
            "decisions": decisions or [],
        }

    def answer(
        self,
        question: str,
        risk_facts: dict[str, Any],
        drivers: list[dict[str, Any]] | None = None,
        decisions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        context = self.build_context(risk_facts, drivers, decisions)
        facts = context["facts"]
        evidence = context["cro_evidence"]
        summary = context["summary"]
        alerts = context["alerts"]

        exposure = evidence.get("exposure", {})
        par = evidence.get("par", {})
        impact = evidence.get("exposure_impact", {})
        migration = evidence.get("migration", {})
        concentration = risk_facts.get("concentration", {})
        segments = facts.get("segments") or concentration.get("segments", [])
        drivers_data = context["drivers"]

        total = exposure.get("total_balance")
        severity = self._severity(summary, facts, alerts)
        evidence_lines = []

        for key, label in (("par30", "PAR30"), ("par60", "PAR60"), ("par90", "PAR90")):
            item = par.get(key)
            if isinstance(item, dict) and isinstance(item.get("ratio"), (int, float)):
                amount = item.get("balance")
                line = "%s: %.2f%%" % (label, item["ratio"] * 100)
                if isinstance(amount, (int, float)):
                    line += " / impacto $%,.2f" % amount
                evidence_lines.append(line)

        if isinstance(total, (int, float)):
            evidence_lines.append("Capital expuesto: $%,.2f" % total)

        executive = [
            "Severidad calculada: %s." % severity,
            "Capital expuesto: $%,.2f." % total if isinstance(total, (int, float)) else "Capital expuesto: Evidencia insuficiente.",
        ]
        par30 = par.get("par30", {})
        if isinstance(par30.get("ratio"), (int, float)):
            line = "Riesgo PAR30: %.2f%%" % (par30["ratio"] * 100)
            if isinstance(impact.get("par30_balance"), (int, float)):
                line += " ($%,.2f)." % impact["par30_balance"]
            executive.append(line)
        else:
            executive.append("Riesgo inmediato: Evidencia insuficiente para cuantificar PAR30.")

        delinquency = []
        for key, label in (("par30", "PAR30"), ("par60", "PAR60"), ("par90", "PAR90")):
            item = par.get(key, {})
            amount = impact.get("%s_balance" % key)
            if isinstance(item, dict) and isinstance(item.get("ratio"), (int, float)):
                line = "%s: %.2f%%" % (label, item["ratio"] * 100)
                if isinstance(amount, (int, float)):
                    line += " ($%,.2f de exposición)" % amount
                delinquency.append(line)

        stress = impact.get("stress_if_30_to_89_migrates_to_90_plus")
        resulting = impact.get("stress_par90_ratio_if_30_to_89_migrates")
        if isinstance(stress, (int, float)):
            line = "Stress determinístico 30–89 → 90+: $%,.2f" % stress
            if isinstance(resulting, (int, float)):
                line += "; PAR90 resultante %.2f%%." % (resulting * 100)
            delinquency.append(line)
        else:
            delinquency.append("Stress 30–89 → 90+: Evidencia insuficiente.")

        early_to_hard = migration.get("early_to_hard", {})
        if migration.get("available"):
            delinquency.append(
                "Rollover Rate observado Mora Temprana → Mora Dura: %.2f%%."
                % (float(early_to_hard.get("roll_rate_by_balance", 0) or 0) * 100)
            )
        else:
            delinquency.append("Rollover Rate: Evidencia insuficiente; se requieren snapshots longitudinales.")

        root_causes = []
        if drivers_data:
            for driver in drivers_data[:3]:
                root_causes.append(
                    "Hecho observado — %s: %s."
                    % (
                        driver.get("title") or driver.get("type") or "driver",
                        driver.get("evidence") or driver.get("message") or "evidencia determinística disponible",
                    )
                )

        for segment in sorted(
            [s for s in segments if isinstance(s, dict)],
            key=lambda s: float(s.get("par30") or 0),
            reverse=True,
        )[:3]:
            segment_par30 = float(segment.get("par30") or 0)
            share = float(segment.get("share_of_exposure", segment.get("share_of_portfolio", 0)) or 0)
            if segment_par30 > 0:
                root_causes.append(
                    "Hipótesis a validar — %s muestra PAR30 de %.2f%% y exposición %.2f%%."
                    % (
                        segment.get("label") or segment.get("segment") or "segmento no identificado",
                        segment_par30 * 100,
                        share * 100,
                    )
                )

        if not root_causes:
            root_causes.append(
                "Evidencia insuficiente para atribuir el deterioro a Underwriting, FPD, Collections, vintage, producto o región."
            )

        mitigation = [
            "Collections: priorizar la Mora Temprana 30–89 DPD por exposición, sujeto a validación operativa.",
            "Collections: revisar los flujos con mayor Rollover Rate observado antes de definir acciones.",
            "Originations/Underwriting: revisar segmentos o vintages con deterioro material; no atribuir causalidad sin indicadores de originación.",
        ]
        if not migration.get("available"):
            mitigation[1] = (
                "Collections: habilitar snapshots longitudinales para medir Rollover Rate antes de inferir velocidad de deterioro."
            )

        answer = (
            "1. Executive Diagnosis\n"
            + "\n".join("- " + line for line in executive)
            + "\n\n2. Delinquency & Migration\n"
            + "\n".join("- " + line for line in delinquency)
            + "\n\n3. Root Causes\n"
            + "\n".join("- " + line for line in root_causes)
            + "\n\n4. Mitigation Strategy\n"
            + "\n".join("- " + line for line in mitigation)
        )

        return {
            "question": question,
            "answer": answer,
            "status": summary.get("status", "unknown"),
            "severity": severity,
            "evidence": evidence_lines,
            "cro_evidence": evidence,
            "drivers": drivers_data[:3],
            "decisions": context["decisions"][:3],
            "decision": {
                "priority": "Collections + Mora Temprana" if migration.get("available") else "Mora y evidencia longitudinal",
                "evidence": evidence_lines,
                "impact": impact,
                "suggested_action": mitigation[0],
                "human_review_required": True,
            },
            "grounded": True,
            "provider": "evidence_mode",
            "mode": "CRO Evidence Mode",
            "prompt_version": "cro-financial-data-scientist-v1",
            "system_prompt": self.CRO_SYSTEM_PROMPT,
            "note": "El motor determinístico calcula la evidencia; esta capa la interpreta sin inventar métricas ni causalidad.",
        }

    @staticmethod
    def _severity(summary: dict[str, Any], facts: dict[str, Any], alerts: list[Any]) -> str:
        status = str(summary.get("status") or "").lower()
        if status in {"critical", "critico", "crítico"}:
            return "Crítico"
        if status in {"warning", "watch", "moderate", "moderado"}:
            return "Moderado"
        for fact_key in ("par90", "par30"):
            fact = facts.get(fact_key)
            if isinstance(fact, dict) and str(fact.get("severity", "")).lower() == "critical":
                return "Crítico"
        if alerts:
            return "Moderado"
        return "Normal"
