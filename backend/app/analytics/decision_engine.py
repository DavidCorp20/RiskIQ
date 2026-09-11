from __future__ import annotations

from typing import Any


class DecisionEngineService:
    """Deterministic risk prioritization layer.

    Converts measured risk signals into review priorities. It does not infer
    causality, approve/deny credit, or execute customer actions.
    """

    def build(self, risk: dict[str, Any], npl: dict[str, Any] | None = None) -> dict[str, Any]:
        par = risk.get("par", {})
        par30 = float(par.get("par30", {}).get("ratio", 0) or 0)
        par60 = float(par.get("par60", {}).get("ratio", 0) or 0)
        par90 = float(par.get("par90", {}).get("ratio", 0) or 0)
        exposure = float(risk.get("exposure", 0) or 0)
        decisions: list[dict[str, Any]] = []

        def add(id_: str, priority: str, title: str, reason: str, evidence: list[str], action: str):
            decisions.append({
                "id": id_, "priority": priority, "title": title,
                "reason": reason, "evidence": evidence,
                "recommended_action": action, "requires_human_review": True,
                "executed": False,
            })

        if par90 >= 0.005:
            add("par90_review", "critical", "Review severe delinquency exposure",
                "PAR90 is above the critical review threshold.",
                [f"PAR90={par90:.2%}", f"exposure={exposure:.2f}"],
                "Prioritize the affected accounts for manual portfolio review.")
        elif par30 >= 0.08:
            add("par30_review", "high", "Review elevated delinquency",
                "PAR30 is above the high-risk review threshold.",
                [f"PAR30={par30:.2%}", f"exposure={exposure:.2f}"],
                "Segment affected accounts and review collection or policy treatment.")
        elif par30 > 0:
            add("par30_monitor", "watch", "Monitor delinquency migration",
                "There is measurable PAR30 exposure below the high-risk threshold.",
                [f"PAR30={par30:.2%}"],
                "Monitor the next portfolio cut and investigate material deterioration.")

        if par60 > par30 + 1e-12:
            add("bucket_inconsistency", "critical", "Investigate delinquency bucket inconsistency",
                "A later delinquency bucket exceeds an earlier bucket.",
                [f"PAR60={par60:.2%}", f"PAR30={par30:.2%}"],
                "Validate source data, bucket definitions and portfolio aggregation before using the metric operationally.")

        if npl and npl.get("available") and float(npl.get("ratio", 0) or 0) > 0:
            ratio = float(npl.get("ratio", 0) or 0)
            add("npl_review", "high" if ratio >= 0.05 else "watch", "Review non-performing exposure",
                "The NPL90 proxy identifies outstanding exposure at 90+ DPD.",
                [f"NPL90_proxy={ratio:.2%}"],
                "Review affected exposures and confirm the applicable regulatory definition before reporting externally.")

        if not decisions:
            add("portfolio_monitor", "healthy", "Continue portfolio monitoring",
                "No deterministic threshold currently requires escalation.",
                [f"PAR30={par30:.2%}", f"PAR90={par90:.2%}"],
                "Continue routine monitoring and reassess on the next dataset snapshot.")

        order = {"critical": 0, "high": 1, "watch": 2, "healthy": 3}
        decisions.sort(key=lambda x: order.get(x["priority"], 9))
        return {
            "available": bool(risk.get("available", False)),
            "decisions": decisions,
            "methodology": {
                "deterministic": True,
                "thresholds_are_explicit": True,
                "causality_inferred": False,
                "customer_actions_executed": False,
                "human_review_required": True,
            },
        }
