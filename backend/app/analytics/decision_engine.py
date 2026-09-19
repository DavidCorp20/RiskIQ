from __future__ import annotations

from typing import Any


class DecisionEngineService:
    """Deterministic risk-to-decision layer with auditable execution trace.

    Converts measured risk into prioritized review decisions. It never infers
    causality, approves/denies credit, or executes customer actions.
    """

    def build(self, risk: dict[str, Any], npl: dict[str, Any] | None = None) -> dict[str, Any]:
        par = risk.get("par", {})
        par30 = float(par.get("par30", {}).get("ratio", 0) or 0)
        par60 = float(par.get("par60", {}).get("ratio", 0) or 0)
        par90 = float(par.get("par90", {}).get("ratio", 0) or 0)
        exposure = float(risk.get("exposure", 0) or 0)
        decisions: list[dict[str, Any]] = []

        def add(id_: str, severity: str, title: str, reason: str, evidence: list[str], action: str):
            order = {"critical": 1, "high": 2, "medium": 3, "low": 4}
            priority = order[severity]
            decision = {
                "id": id_, "priority": priority, "severity": severity, "title": title,
                "reason": reason, "rationale": reason, "evidence": evidence,
                "recommended_action": action, "recommendation": action, "suggested_action": action,
                "trigger": reason, "impact": f"Exposure affected by this signal: {exposure:.2f}.",
                "confidence": "evidence backed · deterministic rule", "requires_human_review": True,
                "human_review_required": True, "executed": False,
            }
            decisions.append(decision)

        if par90 >= 0.005:
            add("par90_review", "critical", "Review severe delinquency exposure",
                "PAR90 is above the critical review threshold.",
                [f"PAR90={par90:.2%}", f"exposure={exposure:.2f}", "threshold=0.50%"],
                "Prioritize affected accounts for manual portfolio review and recovery management.")

        if par30 >= 0.08:
            add("par30_review", "high", "Review elevated delinquency",
                "PAR30 is above the high-risk review threshold.",
                [f"PAR30={par30:.2%}", f"exposure={exposure:.2f}", "threshold=8.00%"],
                "Segment affected accounts and review collection or policy treatment.")
        elif par30 >= 0.05:
            add("par30_monitor", "medium", "Monitor delinquency migration",
                "PAR30 is in the defined monitoring zone below the high-risk threshold.",
                [f"PAR30={par30:.2%}", "monitoring_threshold=5.00%"],
                "Monitor the next portfolio cut and investigate material deterioration.")

        if par60 > par30 + 1e-12:
            add("bucket_inconsistency", "critical", "Investigate delinquency bucket inconsistency",
                "A later delinquency bucket exceeds an earlier bucket.",
                [f"PAR60={par60:.2%}", f"PAR30={par30:.2%}"],
                "Validate source data, bucket definitions and portfolio aggregation before operational use.")

        if npl and npl.get("available") and float(npl.get("ratio", 0) or 0) > 0:
            ratio = float(npl.get("ratio", 0) or 0)
            add("npl_review", "high" if ratio >= 0.05 else "medium", "Review non-performing exposure",
                "The NPL90 proxy identifies outstanding exposure at 90+ DPD.",
                [f"NPL90_proxy={ratio:.2%}", "regulatory_definition=false"],
                "Review affected exposures and confirm the applicable regulatory definition before external reporting.")

        if not decisions:
            add("portfolio_monitor", "low", "Continue portfolio monitoring",
                "No deterministic threshold currently requires escalation.",
                [f"PAR30={par30:.2%}", f"PAR90={par90:.2%}"],
                "Continue routine monitoring and reassess on the next dataset snapshot.")

        decisions.sort(key=lambda x: (x["priority"], x["id"]))
        triggered_rules=[{"rule_id":d["id"],"severity":d["severity"],"condition":d["trigger"],"matched":True} for d in decisions]
        reason_codes=[d["id"] for d in decisions]
        decision_path=[
            {"stage":"FACTS","label":"Facts","evidence":{"PAR30":par30,"PAR60":par60,"PAR90":par90,"exposure":exposure}},
            {"stage":"INDICATORS","label":"Indicators","evidence":"PAR buckets evaluated"},
            {"stage":"RULES","label":"Rules","evidence":len(triggered_rules)},
            {"stage":"DECISION","label":"Decision","evidence":decisions[0]["title"]},
            {"stage":"IMPACT","label":"Impact","evidence":decisions[0]["impact"]},
            {"stage":"HUMAN_REVIEW","label":"Human review","evidence":"Required"},
            {"stage":"AUDIT","label":"Audit","evidence":"Ledger persisted by dataset intelligence"},
        ]
        card_keys=("id","priority","severity","title","reason","rationale","evidence","recommended_action","recommendation","suggested_action","trigger","impact","confidence","requires_human_review","human_review_required","executed")
        cards=[{k:d[k] for k in card_keys} for d in decisions]
        counts={"critical":sum(d["severity"]=="critical" for d in decisions),"high":sum(d["severity"]=="high" for d in decisions),"watch":sum(d["severity"] not in {"critical","high"} for d in decisions),"total_cards":len(cards)}
        return {
            "available": bool(risk.get("available", False)),
            "status": "critical" if decisions[0]["severity"] == "critical" else "high" if decisions[0]["severity"] == "high" else "monitoring",
            "decisions": decisions, "cards": cards, "counts": counts,
            "triggered_rules": triggered_rules, "reason_codes": reason_codes, "decision_path": decision_path,
            "decision_evidence": {"facts":{"PAR30":par30,"PAR60":par60,"PAR90":par90,"exposure":exposure},"triggered_rules":triggered_rules,"reason_codes":reason_codes,"decision":decisions[0]["recommended_action"],"policy":{"id":"risk-intelligence-v1","name":"Dataset Intelligence","version":"v7"}},
            "methodology": {"deterministic":True,"thresholds_are_explicit":True,"causality_inferred":False,"customer_actions_executed":False,"human_review_required":True},
            "governance": {"requires_human_review":True,"customer_actions_executed":False,"ai_is_not_source_of_truth":True},
        }
