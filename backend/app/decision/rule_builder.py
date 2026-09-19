from __future__ import annotations
from typing import Any

SUPPORTED_OPERATORS={"eq","neq","gt","gte","lt","lte","in","not_in","between","contains","not_contains","exists","not_exists"}
SUPPORTED_ACTIONS={"alert","recommend","set_risk_level","review","block"}
SUPPORTED_MODES={"manual","suggested","approval","automatic"}
SUPPORTED_LOGIC={"AND","OR"}
SUPPORTED_EXECUTION={"visual","formula","code"}

class RuleBuilder:
    """Compiles visual, formula and sandboxed code policies into one auditable contract."""
    def validate(self, rule:dict[str,Any])->dict[str,Any]:
        errors=[]; execution=rule.get("execution_mode","visual")
        if not rule.get("id"): errors.append("id is required")
        if not rule.get("name"): errors.append("name is required")
        if rule.get("logic","AND") not in SUPPORTED_LOGIC: errors.append("unsupported logic")
        if rule.get("mode","suggested") not in SUPPORTED_MODES: errors.append("unsupported mode")
        if execution not in SUPPORTED_EXECUTION: errors.append("unsupported execution mode")
        if execution=="code" and not rule.get("code"): errors.append("code is required")
        conditions=rule.get("conditions",[])
        if execution in {"visual","formula"} and not conditions: errors.append("at least one condition is required")
        for i,c in enumerate(conditions):
            if not c.get("field"): errors.append(f"condition {i}: field is required")
            if c.get("operator") not in SUPPORTED_OPERATORS: errors.append(f"condition {i}: unsupported operator")
            if "value" not in c and c.get("operator") not in {"exists","not_exists"}: errors.append(f"condition {i}: value is required")
        actions=rule.get("actions",[])
        if not actions: errors.append("at least one action is required")
        for i,a in enumerate(actions):
            if a.get("type") not in SUPPORTED_ACTIONS: errors.append(f"action {i}: unsupported action")
        normalized=dict(rule); normalized.setdefault("logic","AND"); normalized.setdefault("mode","suggested"); normalized.setdefault("enabled",True); normalized.setdefault("execution_mode","visual"); normalized.setdefault("code",""); normalized.setdefault("version",1)
        return {"valid":not errors,"errors":errors,"normalized_rule":normalized if not errors else None}
    def from_visual(self,payload): return self.validate(payload)
    def compile(self,payload):
        r=self.validate(payload)
        if not r["valid"]: return r
        rule=dict(r["normalized_rule"]); rule["builder_version"]="3.0"; rule["contract"]="decision-engine-v3"
        return {"valid":True,"errors":[],"compiled_rule":rule}
