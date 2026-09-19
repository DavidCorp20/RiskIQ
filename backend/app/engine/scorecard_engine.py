from __future__ import annotations
from typing import Any
from app.engine.formula_engine import FormulaEngine

class ScorecardEngine:
    """Transparent scorecard runtime. Points are additive and traceable."""
    def __init__(self): self.formulas=FormulaEngine()
    def validate(self, scorecard:dict[str,Any])->list[str]:
        errors=[]
        if not isinstance(scorecard,dict): return ["scorecard must be an object"]
        if not scorecard.get("id"): errors.append("scorecard.id is required")
        if not scorecard.get("name"): errors.append("scorecard.name is required")
        for i,item in enumerate(scorecard.get("items",[])):
            if not item.get("id"): errors.append(f"items[{i}].id is required")
            if "formula" not in item and "points" not in item: errors.append(f"items[{i}] requires formula or points")
            if item.get("formula"): errors += [f"items[{i}]: {e}" for e in self.formulas.validate(item["formula"])]
        for i,b in enumerate(scorecard.get("bands",[])):
            if any(k not in b for k in ("min","max","label")): errors.append(f"bands[{i}] requires min, max and label")
        return sorted(set(errors))
    def evaluate(self,facts:dict[str,Any],scorecard:dict[str,Any])->dict[str,Any]:
        errors=self.validate(scorecard)
        if errors: raise ValueError("; ".join(errors))
        working=dict(facts); total=0.0; trace=[]
        for item in scorecard.get("items",[]):
            value=item.get("points",0)
            if item.get("formula"): value=self.formulas.evaluate(working,{item["id"]:item["formula"]})["facts"][item["id"]]
            try: numeric=float(value)
            except (TypeError,ValueError): numeric=0.0
            weight=float(item.get("weight",1) or 1); contribution=numeric*weight; total+=contribution; working[item["id"]]=value
            trace.append({"item_id":item["id"],"name":item.get("name",item["id"]),"raw_value":value,"weight":weight,"contribution":contribution})
        band=next((b for b in scorecard.get("bands",[]) if float(b["min"])<=total<=float(b["max"])),None)
        return {"score":round(total,4),"band":band,"trace":trace,"facts":working}
