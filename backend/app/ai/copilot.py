from __future__ import annotations

from typing import Any


class RiskCopilotService:
    """Executive CRO interpretation layer grounded exclusively in deterministic evidence."""

    CRO_SYSTEM_PROMPT = """Eres el Chief Risk Officer (CRO) y Científico de Datos Financieros Principal de la entidad, dirigiéndote al Comité de Riesgos. Presenta un informe ejecutivo fluido sobre el estado de la cartera utilizando EXCLUSIVAMENTE la evidencia determinística calculada que se proporciona.

REGLAS DE SÍNTESIS Y ESTILO:
- Escribe en prosa continua. No uses viñetas, listas numeradas, tablas ni encabezados numerados.
- No utilices muletillas repetitivas como "Como hecho observado" o "Como hipótesis a validar".
- No dupliques signos de puntuación.
- Sintetiza, agrupa y compara segmentos en lugar de enumerarlos uno por uno.
- Integra cifras en dólares ($), porcentajes y magnitudes de exposición de forma orgánica en lenguaje bancario.
- Trata la distinción entre estrés y forecast con lenguaje natural: el escenario de migración es un ejercicio condicional sobre la exposición observada y no debe presentarse como predicción.
- Presenta scoring, originación, perfil, First Payment Default, Collections, producto, vintage o región como hipótesis de trabajo únicamente cuando exista evidencia que justifique explorarlos; la asociación no basta para afirmar causalidad.
- RiskIQ calcula los números. La narrativa interpreta su significado económico y estratégico. NUNCA inventes, aproximes o deduzcas cifras, tasas, porcentajes, umbrales o resultados.
- Si no existen snapshots longitudinales suficientes, indica de forma natural que la evidencia disponible no permite concluir sobre Rollover Rate ni velocidad de deterioro.
- Las recomendaciones deben ser concretas, condicionales, auditables y sujetas a revisión humana. No presentes acciones como ya ejecutadas.

FORMATO OBLIGATORIO:
La respuesta debe contener exactamente cuatro párrafos narrativos, cada uno precedido por uno de estos subtítulos breves en negrita:
**Situación de la cartera**
**Deterioro y migración**
**Concentraciones e hipótesis de trabajo**
**Prioridades de gestión**

El primer párrafo debe diagnosticar la severidad general, el capital total expuesto y la concentración del riesgo en mora temprana mediante PAR30, estableciendo la prioridad estratégica de contención.

El segundo debe relacionar PAR30, PAR60 y PAR90, cuantificar la brecha de contención en dólares cuando exista evidencia, describir el volumen expuesto al escenario de migración 30–89 DPD hacia 90+ y mencionar el Rollover Rate histórico observado cuando haya snapshots.

El tercero debe comparar y agrupar las concentraciones o segmentos según el deterioro disponible y plantear causas probables como hipótesis de trabajo, señalando qué validación operativa debe realizarse antes de atribuirlas a originación, scoring, perfil u operación.

El cuarto debe establecer prioridades tácticas para Collections con foco en 30–89 DPD y los análisis preventivos que Originations/Underwriting debe ejecutar antes de modificar políticas de crédito.

No uses listas, viñetas, saludos ni numeración. Todo dato cuantitativo debe proceder de EVIDENCE_JSON.
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

    @staticmethod
    def _number(value: Any) -> float | None:
        return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None

    @staticmethod
    def _pct(value: Any) -> str | None:
        number = RiskCopilotService._number(value)
        return f"{number * 100:.2f}%" if number is not None else None

    @staticmethod
    def _money(value: Any) -> str | None:
        number = RiskCopilotService._number(value)
        return f"$ {number:,.2f}" if number is not None else None

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
        concentration = risk_facts.get("concentration", {})
        segments = facts.get("segments") or concentration.get("segments", [])
        drivers_data = context["drivers"]

        exposure = evidence.get("exposure", {}) if isinstance(evidence, dict) else {}
        par = evidence.get("par", {}) if isinstance(evidence, dict) else {}
        impact = evidence.get("exposure_impact", {}) if isinstance(evidence, dict) else {}
        migration = evidence.get("migration", {}) if isinstance(evidence, dict) else {}
        total = exposure.get("total_balance")
        severity = self._severity(summary, facts, alerts)

        evidence_lines: list[str] = []
        for key, label in (("par30", "PAR30"), ("par60", "PAR60"), ("par90", "PAR90")):
            item = par.get(key, {})
            ratio = self._pct(item.get("ratio")) if isinstance(item, dict) else None
            balance = self._money(item.get("balance")) if isinstance(item, dict) else None
            if ratio is not None:
                evidence_lines.append(f"{label}: {ratio}" + (f" / {balance}" if balance else ""))

        total_money = self._money(total)
        if total_money:
            evidence_lines.append(f"Capital expuesto: {total_money}")

        executive = self._executive_narrative(severity, total, par, impact)
        delinquency = self._migration_narrative(par, impact, migration)
        root_causes = self._root_cause_narrative(segments, drivers_data)
        mitigation = self._mitigation_narrative(migration, segments, drivers_data)

        answer_text = (
            "**Situación de la cartera**\n"
            f"{executive}\n\n"
            "**Deterioro y migración**\n"
            f"{delinquency}\n\n"
            "**Concentraciones e hipótesis de trabajo**\n"
            f"{root_causes}\n\n"
            "**Prioridades de gestión**\n"
            f"{mitigation}"
        )

        return {
            "question": question,
            "answer": answer_text,
            "status": summary.get("status", "unknown"),
            "severity": severity,
            "evidence": evidence_lines,
            "cro_evidence": evidence,
            "drivers": drivers_data[:3],
            "decisions": context["decisions"][:3],
            "decision": {
                "priority": "Collections + Mora Temprana" if migration.get("available") else "Mora + evidencia longitudinal",
                "evidence": evidence_lines,
                "impact": impact,
                "suggested_action": mitigation,
                "human_review_required": True,
            },
            "grounded": True,
            "provider": "evidence_mode",
            "mode": "CRO Evidence Mode",
            "prompt_version": "cro-financial-data-scientist-v3",
            "system_prompt": self.CRO_SYSTEM_PROMPT,
            "note": "El motor determinístico calcula la evidencia; esta capa la interpreta en narrativa ejecutiva sin inventar métricas ni causalidad.",
        }

    def _executive_narrative(
        self,
        severity: str,
        total: Any,
        par: dict[str, Any],
        impact: dict[str, Any],
    ) -> str:
        total_money = self._money(total)
        par30 = par.get("par30", {}) if isinstance(par, dict) else {}
        par30_pct = self._pct(par30.get("ratio")) if isinstance(par30, dict) else None
        par30_money = self._money(impact.get("par30_balance"))

        if not total_money:
            return (
                f"La severidad disponible en la evidencia es {severity}, pero existe evidencia insuficiente "
                "para cuantificar el capital total expuesto. La lectura ejecutiva debe limitarse a los indicadores "
                "calculados que sí estén disponibles."
            )

        paragraph = (
            f"La cartera presenta una severidad calculada de {severity}, con un capital total expuesto de "
            f"{total_money}. "
        )
        if par30_pct:
            paragraph += f"El indicador PAR30 se ubica en {par30_pct}"
            if par30_money:
                paragraph += f", equivalente a {par30_money} de exposición"
            paragraph += ". "
        else:
            paragraph += "No existe evidencia calculada suficiente para cuantificar PAR30. "

        paragraph += (
            "En consecuencia, la prioridad analítica debe concentrarse en la porción de exposición que la evidencia "
            "determinística identifica como Mora Temprana y en su capacidad observada de deterioro, sin convertir "
            "estos hallazgos en una proyección futura."
        )
        return paragraph

    def _migration_narrative(
        self,
        par: dict[str, Any],
        impact: dict[str, Any],
        migration: dict[str, Any],
    ) -> str:
        parts: list[str] = []
        for key, label in (("par30", "PAR30"), ("par60", "PAR60"), ("par90", "PAR90")):
            item = par.get(key, {}) if isinstance(par, dict) else {}
            ratio = self._pct(item.get("ratio")) if isinstance(item, dict) else None
            balance = self._money(impact.get(f"{key}_balance"))
            if ratio is not None:
                parts.append(
                    f"{label} es {ratio}" + (f", con {balance} de exposición" if balance else "")
                )

        stress = self._money(impact.get("stress_if_30_to_89_migrates_to_90_plus"))
        stress_ratio = self._pct(impact.get("stress_par90_ratio_if_30_to_89_migrates"))
        if stress:
            stress_text = (
                f"El escenario de estrés determinístico en el que la exposición actualmente situada entre "
                f"30 y 89 DPD migra íntegramente a 90+ DPD representa {stress}"
            )
            if stress_ratio:
                stress_text += f" y llevaría el PAR90 calculado a {stress_ratio}"
            stress_text += ". El resultado representa un ejercicio de estrés condicional sobre la exposición observada y permite dimensionar la severidad potencial bajo esa hipótesis."
            parts.append(stress_text)
        else:
            parts.append(
                "Evidencia insuficiente para cuantificar el escenario determinístico de migración de 30–89 DPD hacia 90+."
            )

        if migration.get("available"):
            early_to_hard = migration.get("early_to_hard", {})
            roll = self._pct(early_to_hard.get("roll_rate_by_balance"))
            transition = self._money(early_to_hard.get("transition_balance"))
            if roll:
                text = f"Los snapshots disponibles muestran un Rollover Rate observado de Mora Temprana a Mora Dura de {roll}"
                if transition:
                    text += f", asociado a {transition} de transición observada"
                text += ". Este indicador resume la transición histórica capturada por los snapshots disponibles y sirve para dimensionar la dinámica de deterioro observada."
                parts.append(text)
        else:
            parts.append(
                "No existen snapshots longitudinales suficientes para medir un Rollover Rate observado. "
                "La evidencia es insuficiente para concluir sobre la velocidad de deterioro entre períodos."
            )

        return " ".join(parts)

    def _root_cause_narrative(
        self,
        segments: Any,
        drivers: list[dict[str, Any]],
    ) -> str:
        observations: list[str] = []
        if drivers:
            for driver in drivers[:3]:
                if not isinstance(driver, dict):
                    continue
                title = driver.get("title") or driver.get("type") or "driver"
                evidence = driver.get("evidence") or driver.get("message")
                if evidence:
                    observations.append(f"{title} presenta {evidence}.")
        segment_items = [s for s in segments if isinstance(s, dict)] if isinstance(segments, list) else []
        segment_items.sort(key=lambda s: self._number(s.get("par30")) or 0, reverse=True)
        for segment in segment_items[:3]:
            par30 = self._pct(segment.get("par30"))
            share = self._pct(segment.get("share_of_exposure", segment.get("share_of_portfolio")))
            label = segment.get("label") or segment.get("segment") or "segmento no identificado"
            if par30:
                sentence = f"{label} concentra un PAR30 de {par30}"
                if share:
                    sentence += f" y representa {share} de la exposición"
                sentence += ", una señal que orienta la revisión hacia las variables de originación y comportamiento disponibles."
                observations.append(sentence)

        if not observations:
            return (
                "La evidencia disponible no permite establecer una causa raíz demostrada. En particular, no se "
                "dispone de indicadores suficientes para atribuir el deterioro a Underwriting, First Payment Default, "
                "Collections, vintage, producto o región."
            )

        return (
            "La evidencia disponible permite focalizar la revisión en determinados vectores de vulnerabilidad. "
            + " ".join(observations)
            + " La lectura causal requiere contrastar estos patrones con indicadores de originación, comportamiento y gestión antes de traducirlos en cambios de política."
        )

    def _mitigation_narrative(
        self,
        migration: dict[str, Any],
        segments: Any,
        drivers: list[dict[str, Any]],
    ) -> str:
        segment_items = [s for s in segments if isinstance(s, dict)] if isinstance(segments, list) else []
        has_segment_evidence = bool(segment_items)
        if migration.get("available"):
            collections = (
                "Para Collections, la intervención táctica debe concentrarse en la Mora Temprana 30–89 DPD "
                "identificada por la evidencia y en los flujos con mayor transición observada, priorizando exposición "
                "antes de que alcance Mora Dura. La acción concreta debe validarse contra capacidad operativa y política vigente."
            )
        else:
            collections = (
                "Para Collections, la prioridad inmediata debe ser preservar la Mora Temprana como foco de contención, "
                "pero la evidencia es insuficiente para ordenar tácticamente los flujos por velocidad de Rollover Rate; "
                "se requieren snapshots longitudinales antes de inferir esa velocidad."
            )

        underwriting = (
            "Para Originations/Underwriting, la evidencia disponible justifica revisar los segmentos o vectores "
            "observados con deterioro, pero no demuestra que la política de originación sea la causa. Cualquier ajuste "
            "de scoring, elegibilidad, límites o condiciones debe pasar por validación cruzada con variables de originación, "
            "First Payment Default y desempeño por vintage antes de activarse."
        )
        if not has_segment_evidence and not drivers:
            underwriting = (
                "Para Originations/Underwriting, no existe evidencia suficiente para recomendar un cambio específico "
                "de política. Primero debe ampliarse la evidencia con segmentación, vintage y variables de originación."
            )

        return collections + " " + underwriting

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
