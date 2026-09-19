from __future__ import annotations

from typing import Any

from app.core.ai.provider import AIProvider, get_ai_provider
from app.services.market_context import MarketContextProvider


class RiskCopilotService:
    """Conversational CRO layer grounded in deterministic evidence with optional Gemini generation."""

    def __init__(self, provider: AIProvider | None = None, market_context: MarketContextProvider | None = None) -> None:
        self.provider = provider if provider is not None else get_ai_provider()
        self.market_context = market_context if market_context is not None else MarketContextProvider()

    CRO_SYSTEM_PROMPT = """Eres el Chief Risk Officer (CRO) y un analista financiero experto en riesgos de crédito. Conversas directamente con un analista o directivo a través de un chat interactivo.

DIRECTRICES DE CONVERSACIÓN:
1. ADAPTABILIDAD TOTAL: Responde de forma directa, natural y conversacional a lo que el usuario pregunte o solicite. Si pide un resumen, entrega un resumen. Si pregunta por un segmento, analiza únicamente ese segmento. Si pregunta por migración, explica la migración. No uses una plantilla estática ni una estructura obligatoria de cuatro partes salvo que el usuario la solicite expresamente.
2. FLUIDEZ Y PROSA NATURAL: Escribe como un profesional humano de riesgo de crédito. Evita viñetas, listas numeradas, tablas y estructuras mecánicas salvo que el usuario las solicite. No uses dobles puntos ni puntuación duplicada. Agrupa, compara y sintetiza cuando la evidencia lo permita.
3. RIGOR DETERMINÍSTICO: Utiliza exclusivamente la evidencia financiera calculada por RiskIQ. Exposición total, PAR30, PAR60, PAR90, brechas, estrés determinístico, Roll Rate, segmentos y cualquier otra cifra deben provenir de EVIDENCE_JSON. Nunca inventes, aproximes ni calcules por tu cuenta una cifra que no esté disponible en la evidencia.
4. INTERPRETACIÓN, NO INVENCIÓN: RiskIQ calcula los indicadores y tú interpretas su significado económico y de riesgo. No atribuyas causalidad a scoring, originación, perfil, Collections, Underwriting, producto, vintage o región sin evidencia específica. Cuando falte evidencia, dilo de manera natural y breve.
5. MIGRACIÓN Y ESTRÉS: El escenario 30–89 DPD hacia 90+ es un ejercicio condicional sobre la exposición observada. El Roll Rate disponible representa transición histórica observada en snapshots y no debe presentarse como predicción.
6. CERO MULETILLAS: No repitas fórmulas como "Como hecho observado", "Como hipótesis a validar", "por lo que corresponde contrastar" o descargos equivalentes en cada oración. Formula las hipótesis de trabajo de manera orgánica y vinculada a la evidencia.
7. TONO: Profesional, analítico, directo al grano y colaborativo. Habla con lenguaje de riesgo bancario cuando corresponda, pero prioriza claridad.
8. ACCIONES: Cuando el usuario pida recomendaciones, prioriza acciones concretas y condicionadas a la evidencia. Para Collections, considera la Mora Temprana 30–89 DPD y la transición observada. Para Underwriting, considera validaciones de originación, FPD, vintage, scoring, elegibilidad y límites antes de proponer cambios de política.

La respuesta debe adaptarse a la intención concreta del usuario. No añadas secciones que no aporten a la pregunta. Todo dato cuantitativo debe proceder de EVIDENCE_JSON.
"""

    @staticmethod
    def _conversation_mode(question: str) -> str:
        """Classify only enough to decide whether risk evidence should reach the LLM."""
        q = " ".join(str(question or "").strip().lower().split())
        analytical_terms = (
            "par30", "par60", "par90", "dpd", "exposicion", "exposición", "cartera", "credito", "crédito",
            "riesgo", "roll rate", "rollover", "migracion", "migración", "vintage", "concentracion",
            "concentración", "npl", "morosidad", "cobranzas", "collections", "segmento", "segment",
            "underwriting", "originacion", "originación", "fpd", "comite", "comité", "decision", "decisión",
            "mora", "90+", "90 +", "30-89", "30 – 89",
        )
        return "analytical" if any(term in q for term in analytical_terms) else "conversational"

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
            "conversation": conversation or [],
        }

    MARKET_CONTEXT_SYSTEM_RULES = """REGLAS INQUEBRANTABLES SOBRE MARKET CONTEXT:
1. MARKET_CONTEXT es exclusivamente contexto externo para la interpretación cualitativa del CRO.
2. Nunca uses MARKET_CONTEXT para recalcular, corregir, sustituir o modificar PAR30, PAR60, PAR90, NPL, exposición, Roll Rate, severity ni ningún indicador determinístico de RiskIQ.
3. Nunca establezcas causalidad directa entre un movimiento de mercado y el deterioro de la cartera. Correlación temporal no demuestra causalidad.
4. Si MARKET_CONTEXT está unavailable, partial, disabled o stale, continúa funcionando con RiskIQ evidence.
5. Nunca inventes datos macroeconómicos o de mercado ausentes del contexto recibido.
6. NQ Futures es una señal externa de mercado y no una predicción del desempeño crediticio.
7. La evidencia determinística de RiskIQ siempre tiene precedencia sobre cualquier contexto externo.
"""

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
        conversation: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        context = self.build_context(risk_facts, drivers, decisions, conversation)
        mode = self._conversation_mode(question)
        facts = context["facts"]
        evidence = context["cro_evidence"]
        summary = context["summary"]
        alerts = context["alerts"]
        concentration = risk_facts.get("concentration", {})
        segments = facts.get("segments") or concentration.get("segments", [])
        drivers_data = context["drivers"]

        market_context = (
            await self.market_context.get_context()
            if mode == "analytical"
            else {
                "status": "not_requested",
                "source": "RiskIQ MarketContextProvider",
                "as_of": None,
                "ttl_seconds": self.market_context.cache_ttl_seconds,
                "cache": "not_requested",
                "data": {},
                "errors": [],
            }
        )

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

        answer_text, provider_used = await self._generate_conversational_answer(
            question=question,
            mode=mode,
            risk_facts=risk_facts,
            market_context=market_context,
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
            "market_context": market_context,
            "market_context_used": mode == "analytical" and market_context.get("status") in {"available", "partial"},
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
            "provider": provider_used,
            "mode": "CRO Evidence Mode",
            "prompt_version": "cro-dual-mode-v1",
            "conversation_mode": mode,
            "system_prompt": self.CRO_SYSTEM_PROMPT,
            "note": "El motor determinístico establece los hechos; Gemini adapta la interpretación al contexto y a la intención de la conversación sin inventar métricas ni causalidad.",
        }

    async def _generate_conversational_answer(
        self,
        question: str,
        mode: str,
        risk_facts: dict[str, Any],
        market_context: dict[str, Any],
        conversation: list[dict[str, Any]],
        fallback: Any,
    ) -> tuple[str, str]:
        if mode == "conversational":
            context = {
                "MODE": "conversational",
                "CONVERSATION": conversation[-12:],
                "CURRENT_QUESTION": question,
            }
            prompt = (
                f"{self.CRO_SYSTEM_PROMPT}\n\n"
                "MODO ACTUAL: CONVERSACIONAL. No recibes evidencia de cartera porque la pregunta no requiere análisis financiero. "
                "Responde de forma humana, breve y natural. Si corresponde, pregunta qué desea analizar el usuario. "
                "No introduzcas PAR, exposición, mora ni otras métricas por iniciativa propia. "
                'Devuelve exactamente JSON con esta forma {"answer":"texto"}.'
            )
        else:
            context = {
                "MODE": "analytical",
                "EVIDENCE_JSON": risk_facts.get("cro_evidence", {}),
                "FACTS": risk_facts.get("facts", {}),
                "CONCENTRATION": risk_facts.get("concentration", {}),
                "VINTAGE": risk_facts.get("vintage", []),
                "DRIVERS": risk_facts.get("drivers", []),
                "DECISIONS": risk_facts.get("decisions", []),
                "CONVERSATION": conversation[-12:],
                "CURRENT_QUESTION": question,
                "MARKET_CONTEXT": market_context,
            }
            prompt = (
                f"{self.CRO_SYSTEM_PROMPT}\n\n{self.MARKET_CONTEXT_SYSTEM_RULES}\n\n"
                "MODO ACTUAL: ANALÍTICO. Responde como CRO de comité de riesgos. Usa únicamente la evidencia disponible y "
                "las cifras estrictamente necesarias para responder. Mantén continuidad con CONVERSATION. "
                "Puedes explicar, comparar, resumir, profundizar o recomendar según la intención. "
                "No calcules métricas nuevas ni inventes causalidad. El estrés es condicional y el Rollover Rate es histórico. "
                'Usa una estructura profesional solo cuando ayude a la consulta. Devuelve exactamente JSON con esta forma {"answer":"texto"}.'
            )
        try:
            result = await self.provider.generate(prompt, context)
            answer = result.get("answer")
            if isinstance(answer, str) and answer.strip():
                return answer.strip(), "gemini"
        except Exception as exc:
            # Never expose secrets or provider payloads, but keep the failure visible in Railway logs.
            print(f"RiskIQ Gemini provider failed: {type(exc).__name__}: {exc}")
        if mode == "conversational":
            return self._conversational_fallback(question), "conversational_fallback"
        return fallback(), "evidence_mode"

    @staticmethod
    def _conversational_fallback(question: str) -> str:
        q = " ".join(str(question or "").strip().split())
        if not q:
            return "Hola. Soy el copiloto de RiskIQ. Puedo conversar contigo y, cuando quieras analizar la cartera, revisar PAR, morosidad, exposición, migración y otros indicadores calculados."
        greetings = ("hola", "holi", "hello", "buenas", "buenos dias", "buenas tardes", "buenas noches")
        if q.lower().rstrip("!?.,") in greetings:
            return "Hola. Soy el copiloto de RiskIQ. ¿Qué quieres revisar o hacer?"
        return "Claro. Puedo ayudarte con eso. Si quieres pasar al análisis de cartera, dime qué aspecto quieres revisar y utilizaré la evidencia calculada de RiskIQ."


    def _adaptive_narrative(
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
            normalized_q = q.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            normalized_label = label.lower().replace("segmento ", "").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            normalized_key = key.lower().replace("segmento ", "").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            if normalized_label and normalized_label in normalized_q or normalized_key and normalized_key in normalized_q:
                return self._segment_narrative(label, segment)

        if any(term in q for term in ("par90", "par 90")):
            return self._metric_narrative("PAR90", par.get("par90", {}), impact.get("par90_balance"))

        if any(term in q for term in ("par60", "par 60")):
            return self._metric_narrative("PAR60", par.get("par60", {}), impact.get("par60_balance"))

        if any(term in q for term in ("par30", "par 30")):
            return self._metric_narrative("PAR30", par.get("par30", {}), impact.get("par30_balance"))

        if any(term in q for term in ("exposición", "exposicion", "capital expuesto", "saldo total")):
            money = self._money(total)
            loans = sum(int(s.get("loans") or 0) for s in segment_items)
            text = f"La exposición total calculada es {money}." if money else "La evidencia no contiene una exposición total calculada."
            if loans:
                text += f" La segmentación disponible representa {loans} créditos."
            return text

        if any(term in q for term in ("por qué", "porque", "causa", "causas", "motivo", "motivos", "deterioro")):
            return self._root_cause_narrative(segments, drivers)

        if any(term in q for term in ("migración", "migracion", "rollover", "roll rate", "roll-rate", "mora dura", "90+", "90 +")):
            return self._migration_narrative(par, impact, migration)

        if any(term in q for term in ("cobranzas", "collections", "cobranza", "acción", "accion", "prioridad", "qué debería revisar", "que deberia revisar", "revisar primero")):
            return self._mitigation_narrative(migration, segment_items, drivers)

        if any(term in q for term in ("resumen", "situación", "situacion", "estado", "cartera", "exposición", "exposicion", "riesgo general", "overview")) or not q:
            return self._executive_narrative(severity, total, par, impact)

        return self._general_narrative(severity, total, par, impact, migration, segment_items, drivers)

    def _metric_narrative(self, label: str, metric: dict[str, Any], impact_balance: Any) -> str:
        if not isinstance(metric, dict):
            return f"La evidencia disponible no contiene un {label} calculado."

        ratio = self._pct(metric.get("ratio"))
        balance = self._money(impact_balance if impact_balance is not None else metric.get("balance"))
        loans = metric.get("loans")

        if ratio is None:
            return f"La evidencia disponible no contiene un {label} calculado suficiente para responder con una cifra."

        text = f"El {label} calculado es {ratio}"
        if balance:
            text += f", equivalente a {balance} de exposición"
        if isinstance(loans, int):
            text += f", distribuida en {loans} créditos"
        return text + ". La cifra proviene directamente del motor determinístico de RiskIQ."

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
