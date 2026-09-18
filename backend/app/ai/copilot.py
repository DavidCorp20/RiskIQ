from __future__ import annotations

from typing import Any


class RiskCopilotService:
    """Conversational CRO layer grounded in deterministic evidence with optional Gemini generation."""

    def __init__(self, provider: AIProvider | None = None) -> None:
        self.provider = provider if provider is not None else get_ai_provider()

    CRO_SYSTEM_PROMPT = """Eres el Chief Risk Officer (CRO) y un analista financiero experto en riesgos de crédito. Estás conversando de forma totalmente abierta y fluida en un chat interactivo con un miembro del equipo de riesgos.

LIBERTAD TOTAL DE CONVERSACIÓN

No sigues ninguna plantilla ni estructura fija. Responde exactamente a lo que el usuario está preguntando en ese momento.

Si te saludan, saluda de forma natural y pregunta qué desea analizar. Si hacen una pregunta puntual, responde puntualmente. Si quieren profundizar, profundiza. Si cambian de tema, acompaña el cambio sin volver automáticamente al análisis general. Si piden un informe formal, puedes adoptar una estructura formal.

No tienes obligación de mencionar PAR30, PAR60, PAR90, exposición, Rollover Rate, vintage, concentración u otras métricas si no son relevantes para la pregunta. No conviertas una pregunta puntual en un informe completo.

CONTINUIDAD

Utiliza el contexto de conversación proporcionado. Las preguntas de seguimiento como "¿y por qué?", "¿qué significa eso?", "¿y Microcrédito?", "¿qué harías?" deben interpretarse en relación con lo hablado anteriormente. No obligues al usuario a repetir información ya disponible.

TONO

Habla como un CRO conversando con otro profesional de riesgo. Sé analítico, directo, claro, cercano y colaborativo. No escribas como un generador automático de reportes. La estructura debe surgir de la conversación y de la necesidad del usuario.

FIDELIDAD DE DATOS

La evidencia determinística de RiskIQ es la fuente de verdad. Utiliza cifras únicamente cuando sean necesarias y exclusivamente cuando estén presentes en la evidencia proporcionada. Nunca inventes métricas, porcentajes, montos, tasas, cantidades o resultados. No recalcules una métrica que no esté disponible. Si falta información necesaria, dilo claramente.

INTERPRETACIÓN

Puedes interpretar la evidencia y plantear hipótesis de trabajo, pero nunca presentar una hipótesis como causalidad demostrada. Distingue entre lo que los datos muestran, lo que sugieren y lo que todavía necesita investigación.

DECISIONES

Cuando el usuario pregunte qué hacer, qué revisar o dónde intervenir, utiliza la evidencia disponible. Las recomendaciones deben ser proporcionales a la evidencia y no implican automáticamente cambios de política.

MIGRACIÓN Y ESTRÉS

Los Roll Rates son transiciones históricas observadas en los snapshots. Los escenarios de estrés son ejercicios condicionales sobre la exposición observada. Ninguno debe presentarse como una predicción.

PRINCIPIO FUNDAMENTAL

No estás generando un reporte. Estás conversando con un profesional de riesgos. Tu función es convertir la evidencia de RiskIQ en comprensión, diagnóstico y discusión útil, con libertad conversacional y sin inventar información.
"""

    def build_context(
        self,
        risk_facts: dict[str, Any],
        drivers: list[dict[str, Any]] | None = None,
        decisions: list[dict[str, Any]] | None = None,
        conversation: list[dict[str, Any]] | None = None,
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

    async def answer(
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

        answer_text = await self._generate_conversational_answer(
            question=question,
            risk_facts=risk_facts,
            conversation=conversation or [],
            fallback=lambda: self._adaptive_narrative(
                question,
                severity,
                total,
                par,
                impact,
                migration,
                segments,
                drivers_data,
            ),
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
            "prompt_version": "cro-interactive-risk-analyst-v5",
            "system_prompt": self.CRO_SYSTEM_PROMPT,
            "note": "El motor determinístico establece los hechos; Gemini mantiene una conversación abierta y adapta la interpretación al contexto y a la intención del usuario.",
        }

    async def _generate_conversational_answer(
        self,
        question: str,
        risk_facts: dict[str, Any],
        conversation: list[dict[str, Any]],
        fallback: Any,
    ) -> str:
        context = {
            "EVIDENCE_JSON": risk_facts.get("cro_evidence", {}),
            "FACTS": risk_facts.get("facts", {}),
            "CONCENTRATION": risk_facts.get("concentration", {}),
            "VINTAGE": risk_facts.get("vintage", []),
            "DRIVERS": risk_facts.get("drivers", []),
            "DECISIONS": risk_facts.get("decisions", []),
            "CONVERSATION": conversation[-12:],
            "CURRENT_QUESTION": question,
        }
        prompt = (
            "Responde al CURRENT_QUESTION como CRO de RiskIQ. Mantén continuidad con CONVERSATION y responde "
            "solo lo que se pregunta. Si el usuario cambia de tema, cambia de foco sin repetir un informe general. "
            "Puedes explicar, comparar, resumir, profundizar o recomendar según la intención. "
            "Usa únicamente cifras presentes en EVIDENCE_JSON, FACTS, CONCENTRATION, VINTAGE, DRIVERS o DECISIONS. "
            "Si una cifra o dimensión no está disponible, indícalo brevemente. "
            "No calcules métricas nuevas. No inventes causalidad. El escenario de migración es condicional y el "
            "Rollover Rate es histórico, no una predicción. Redacta en español natural, como una conversación entre "
            "profesionales de riesgo, sin encabezados obligatorios, sin viñetas y sin listas salvo que el usuario las pida. "
            "Devuelve exactamente JSON con esta forma {\"answer\":\"texto\"}."
        )
        try:
            result = await self.provider.generate(prompt, context)
            answer = result.get("answer")
            if isinstance(answer, str) and answer.strip():
                return answer.strip()
        except (RuntimeError, ValueError, TypeError, KeyError, Exception):
            pass
        return fallback()


        self,
        question: str,
        severity: str,
        total: Any,
        par: dict[str, Any],
        impact: dict[str, Any],
        migration: dict[str, Any],
        segments: Any,
        drivers: list[dict[str, Any]],
    ) -> str:
        q = (question or "").strip().lower()
        segment_items = [s for s in segments if isinstance(s, dict)] if isinstance(segments, list) else []

        for segment in segment_items:
            label = str(segment.get("label") or segment.get("segment") or "").strip()
            key = str(segment.get("key") or "").strip()
            if label and (label.lower() in q or key.lower() in q):
                return self._segment_narrative(label, segment)

        if any(term in q for term in ("migración", "migracion", "rollover", "roll rate", "roll-rate", "mora dura", "90+", "90 +")):
            return self._migration_narrative(par, impact, migration)

        if any(term in q for term in ("cobranzas", "collections", "cobranza", "acción", "accion", "prioridad", "qué debería revisar", "que deberia revisar", "revisar primero")):
            return self._mitigation_narrative(migration, segment_items, drivers)

        if any(term in q for term in ("resumen", "situación", "situacion", "estado", "cartera", "exposición", "exposicion", "riesgo general", "overview")) or not q:
            return self._executive_narrative(severity, total, par, impact)

        return self._general_narrative(severity, total, par, impact, migration, segment_items, drivers)

    def _segment_narrative(self, label: str, segment: dict[str, Any]) -> str:
        par30 = self._pct(segment.get("par30"))
        balance = self._money(segment.get("balance"))
        share = self._pct(segment.get("share_of_exposure", segment.get("share_of_portfolio")))
        loans = segment.get("loans")
        if not par30:
            return f"La evidencia disponible para {label} no contiene un PAR30 calculado suficiente para caracterizar su deterioro."
        text = f"{label} registra un PAR30 de {par30}"
        if balance:
            text += f", sobre una exposición de {balance}"
        if share:
            text += f", que representa {share} de la exposición total"
        if isinstance(loans, int):
            text += f", distribuida en {loans} créditos"
        return text + ". Este nivel permite focalizar la revisión del segmento dentro de la cartera y contrastarlo con los demás grupos disponibles, sin atribuir por sí solo una causa al deterioro."

    def _general_narrative(
        self,
        severity: str,
        total: Any,
        par: dict[str, Any],
        impact: dict[str, Any],
        migration: dict[str, Any],
        segments: list[dict[str, Any]],
        drivers: list[dict[str, Any]],
    ) -> str:
        parts = [self._executive_narrative(severity, total, par, impact)]
        if migration.get("available"):
            early_to_hard = migration.get("early_to_hard", {})
            roll = self._pct(early_to_hard.get("roll_rate_by_balance"))
            if roll:
                parts.append(f"Los snapshots disponibles muestran un Rollover Rate observado de {roll} entre Mora Temprana y Mora Dura, lo que aporta contexto sobre la dinámica histórica de deterioro.")
        if len(segments) >= 2:
            ordered = sorted(segments, key=lambda s: self._number(s.get("par30")) or 0, reverse=True)
            high = ordered[0]
            low = ordered[-1]
            high_pct = self._pct(high.get("par30"))
            low_pct = self._pct(low.get("par30"))
            if high_pct and low_pct:
                parts.append(f"La mayor presión relativa se concentra en {high.get('label')}, con PAR30 de {high_pct}, mientras {low.get('label')} registra {low_pct}; esta diferencia orienta dónde profundizar la revisión de originación y comportamiento.")
        return " ".join(parts)

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
