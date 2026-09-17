from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.analytics.risk_analytics import RiskAnalyticsService


class RiskIntelligenceService:
    """Evidence-first second-order risk analysis for the operating system."""

    def analyze(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        current = RiskAnalyticsService.latest_snapshot(rows)
        if not current:
            return {"version": "risk-intelligence-v1", "posture": {}, "materiality": {}, "concentration": [], "priorities": [], "data_quality": {"score": 0, "confidence": "low", "checks": [], "limitations": []}}

        balance = sum(self._num(r.get("outstanding_principal", r.get("outstanding_balance"))) for r in current)
        loans = len(current)
        bad = {b: sum(self._num(r.get("outstanding_principal", r.get("outstanding_balance"))) for r in current if self._num(r.get("dpd")) >= b) for b in (1, 7, 30, 60, 90)}
        par = {b: (bad[b] / balance if balance else 0) for b in bad}
        posture = self._posture(par)
        concentration = self._concentration(current, balance, bad[30])
        priorities = self._priorities(concentration, par, bad)
        quality = self._quality(rows, current)

        return {"version": "risk-intelligence-v1", "posture": posture, "materiality": {"exposure": round(balance, 2), "bad_balance_1_plus": round(bad[1], 2), "bad_balance_30_plus": round(bad[30], 2), "bad_balance_60_plus": round(bad[60], 2), "bad_balance_90_plus": round(bad[90], 2), "shares": {f"par{b}": round(par[b], 4) for b in (7, 30, 60, 90)}}, "concentration": concentration, "priorities": priorities, "data_quality": quality, "interpretation": self._interpretation(posture, concentration, par, quality), "definitions": {"exposure": "Outstanding principal/saldo pendiente de los créditos activos en el último corte por crédito.", "par30": "Saldo pendiente de créditos con DPD >= 30 dividido por la exposición total del corte.", "par90": "Saldo pendiente de créditos con DPD >= 90 dividido por la exposición total del corte.", "materiality": "Peso del segmento sobre la exposición total; no implica deterioro.", "severity": "Porcentaje del saldo del segmento que está en 30+ o 90+ según la métrica.", "contribution_to_bad_30": "Participación del segmento en el saldo total 30+ de la cartera.", "early_deterioration": "PAR30 / PAR7; relación observada entre buckets, no una inferencia causal.", "severe_conversion": "PAR90 / PAR30; relación observada entre buckets, no una predicción."}, "governance": {"deterministic": True, "priority_score_is_internal": True, "no_causality_claim": True, "no_customer_action_executed": True, "point_in_time": True}}

    def _concentration(self, rows: list[dict[str, Any]], total: float, bad30: float) -> list[dict[str, Any]]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in rows:
            dimension = str(r.get("segment") or r.get("product") or r.get("product_id") or r.get("product_name") or "Sin segmentación").strip() or "Sin segmentación"
            groups[dimension].append(r)
        out = []
        portfolio_par30 = bad30 / total if total else 0
        for name, items in groups.items():
            exposure = sum(self._num(r.get("outstanding_principal", r.get("outstanding_balance"))) for r in items)
            b30 = sum(self._num(r.get("outstanding_principal", r.get("outstanding_balance"))) for r in items if self._num(r.get("dpd")) >= 30)
            b90 = sum(self._num(r.get("outstanding_principal", r.get("outstanding_balance"))) for r in items if self._num(r.get("dpd")) >= 90)
            share = exposure / total if total else 0
            par30 = b30 / exposure if exposure else 0
            contribution = b30 / bad30 if bad30 else 0
            excess = par30 - portfolio_par30
            severity = self._severity(par30)
            if b30 <= 0 or par30 <= 0:
                score = 0.0
            else:
                severity_factor = 1 + (1 if severity == "critical" else .5 if severity == "high" else 0)
                score = min(100, round(100 * share * severity_factor * (1 + min(2, max(0, excess * 5))) * (0.5 + 0.5 * contribution), 1))
            out.append({"name": name, "loans": len(items), "exposure": round(exposure, 2), "exposure_share": round(share, 4), "bad_balance_30_plus": round(b30, 2), "bad_balance_90_plus": round(b90, 2), "par30": round(par30, 4), "par90": round(b90 / exposure if exposure else 0, 4), "contribution_to_portfolio_bad_30": round(contribution, 4), "excess_par30_vs_portfolio": round(excess, 4), "priority_score": score, "risk_level": severity, "risk_status": "deteriorated" if b30 > 0 else "healthy"})
        return sorted(out, key=lambda x: (-x["priority_score"], -x["exposure"]))[:12]

    def _priorities(self, concentration: list[dict[str, Any]], par: dict[int, float], bad: dict[int, float]) -> list[dict[str, Any]]:
        priorities = []
        if par[90] >= .02:
            priorities.append({"rank": 1, "type": "recovery", "title": "Recuperación de 90+", "evidence": {"par90": round(par[90], 4), "exposure": round(bad[90], 2)}, "why": "La mora severa representa una exposición material que requiere cuantificación de antigüedad y capacidad de recuperación."})
        if par[30] >= .10:
            priorities.append({"rank": len(priorities) + 1, "type": "entry", "title": "Entrada y acumulación en 30+", "evidence": {"par30": round(par[30], 4), "exposure": round(bad[30], 2)}, "why": "La cartera presenta deterioro temprano suficiente para investigar dónde se origina y qué segmentos lo explican."})
        for item in concentration:
            if item["bad_balance_30_plus"] > 0 and item["priority_score"] >= 20:
                priorities.append({"rank": len(priorities) + 1, "type": "concentration", "title": f"Revisar {item['name']}", "evidence": {"exposure_share": item["exposure_share"], "par30": item["par30"], "bad30_contribution": item["contribution_to_portfolio_bad_30"], "priority_score": item["priority_score"]}, "why": "Combina materialidad, severidad y contribución observada a la mora; el score ordena la revisión y no representa una clasificación regulatoria."})
        return priorities[:6]

    @staticmethod
    def _posture(par: dict[int, float]) -> dict[str, Any]:
        if par[90] >= .02 or par[30] >= .20: level = "critical"
        elif par[90] >= .01 or par[30] >= .10: level = "high"
        elif par[90] >= .005 or par[30] >= .05: level = "watch"
        else: level = "control"
        return {"level": level, "label": {"critical": "Riesgo crítico", "high": "Riesgo alto", "watch": "Vigilancia", "control": "Control"}[level], "basis": "PAR30/PAR90 balance-weighted internal thresholds"}

    @staticmethod
    def _severity(par30: float) -> str:
        return "critical" if par30 >= .20 else "high" if par30 >= .10 else "watch" if par30 >= .05 else "control"

    @staticmethod
    def _quality(all_rows: list[dict[str, Any]], current: list[dict[str, Any]]) -> dict[str, Any]:
        n = len(all_rows)
        checks = []
        for key, label in (("dpd", "DPD"), ("outstanding_principal", "saldo"), ("origination_date", "fecha de originación"), ("segment", "segmento")):
            present = sum(1 for r in current if r.get(key) not in (None, ""))
            ratio = present / len(current) if current else 0
            checks.append({"field": key, "label": label, "coverage": round(ratio, 4), "status": "ok" if ratio >= .95 else "partial" if ratio >= .70 else "weak"})
        ids = [str(r.get("loan_id") or r.get("id") or "") for r in current]
        unique_ids = len(set(x for x in ids if x))
        id_coverage = sum(bool(x) for x in ids) / len(current) if current else 0
        checks.append({"field": "loan_id", "label": "identidad de crédito", "coverage": round(id_coverage, 4), "status": "ok" if id_coverage >= .95 and unique_ids == len([x for x in ids if x]) else "weak"})
        score = round(sum(c["coverage"] for c in checks) / len(checks) * 100) if checks else 0
        return {"score": score, "confidence": "high" if score >= 90 else "medium" if score >= 75 else "low", "checks": checks, "records_total": n, "current_loans": len(current), "limitation": "La calidad mide cobertura de campos analíticos; no valida por sí sola la veracidad económica del origen.", "limitations": ["No se puede inferir tendencia temporal ni velocidad de deterioro con un único snapshot.", "Los roll rates requieren al menos dos snapshots comparables y la misma identidad de crédito.", "NPL se trata como proxy de exposición 90+ y no como definición regulatoria.", "Confirmar que outstanding_principal represente saldo pendiente y no principal original/desembolsado antes de interpretar exposición y PAR."]}

    @staticmethod
    def _interpretation(posture: dict[str, Any], concentration: list[dict[str, Any]], par: dict[int, float], quality: dict[str, Any]) -> str:
        deteriorated = [item for item in concentration if item["bad_balance_30_plus"] > 0]
        top = deteriorated[0] if deteriorated else None
        if top:
            return f"{posture['label']}. El segmento con mayor prioridad entre los deteriorados es {top['name']}, con {top['exposure_share']*100:.1f}% de exposición y {top['contribution_to_portfolio_bad_30']*100:.1f}% de la mora 30+. La prioridad combina materialidad, severidad y contribución observada."
        return f"{posture['label']}. No se observan segmentos deteriorados en 30+ en el corte actual. Confianza de datos: {quality['confidence']}."

    @staticmethod
    def _num(value: Any) -> float:
        try: return float(value or 0)
        except (TypeError, ValueError): return 0.0
