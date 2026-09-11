from typing import Any
from app.api.schemas import DecisionRule
from app.engine.formula_engine import FormulaEngine
import ast

SUPPORTED_OPERATORS = {"eq", "neq", "gt", "gte", "lt", "lte", "in", "not_in", "between", "contains", "not_contains", "exists", "not_exists"}
SUPPORTED_LOGIC = {"AND", "OR"}
SAFE_FUNCTIONS = {"abs": abs, "min": min, "max": max, "round": round, "len": len, "to_number": lambda x, default=0: _to_number(x, default), "to_text": lambda x: "" if x is None else str(x), "upper": lambda x: "" if x is None else str(x).upper(), "lower": lambda x: "" if x is None else str(x).lower(), "coalesce": lambda *xs: next((x for x in xs if x not in (None, "")), None)}

def _to_number(value: Any, default: float = 0) -> float:
    try:
        if value is None or value == "": return default
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError): return default

class SafeCodeRunner:
    """Small deterministic Risk DSL. No imports, IO, attributes or arbitrary builtins."""
    ALLOWED = (ast.Module, ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Name, ast.Constant, ast.Dict, ast.List, ast.Tuple, ast.If, ast.Expr, ast.Return, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.USub, ast.UAdd, ast.And, ast.Or, ast.Not, ast.Eq, ast.NotEq, ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.In, ast.NotIn, ast.Call, ast.keyword, ast.Subscript, ast.Load, ast.Store, ast.IfExp)
    BLOCKED_NAMES = {"__import__", "eval", "exec", "open", "compile", "globals", "locals", "getattr", "setattr", "delattr", "input"}
    def validate(self, code: str) -> list[str]:
        errors=[]
        if not code or not code.strip(): return ["code is required"]
        if len(code)>12000: return ["code exceeds 12,000 characters"]
        try: tree=ast.parse(code,mode="exec")
        except SyntaxError as exc: return [f"syntax error: line {exc.lineno}: {exc.msg}"]
        for node in ast.walk(tree):
            if not isinstance(node,self.ALLOWED): errors.append(f"unsupported construct: {type(node).__name__}")
            if isinstance(node,ast.Name) and node.id in self.BLOCKED_NAMES: errors.append(f"blocked name: {node.id}")
            if isinstance(node,ast.Attribute): errors.append("attribute access is not allowed")
            if isinstance(node,(ast.Import,ast.ImportFrom,ast.While,ast.For,ast.FunctionDef,ast.ClassDef,ast.Lambda,ast.Try,ast.With,ast.Delete)): errors.append(f"unsupported construct: {type(node).__name__}")
            if isinstance(node,ast.Call) and (not isinstance(node.func,ast.Name) or node.func.id not in SAFE_FUNCTIONS): errors.append("only approved helper functions can be called")
        return sorted(set(errors))
    def run(self,facts:dict[str,Any],code:str)->Any:
        errors=self.validate(code)
        if errors: raise ValueError("; ".join(errors))
        tree=ast.parse(code,mode="exec"); env={**SAFE_FUNCTIONS,**facts}; result=None
        for node in tree.body:
            if isinstance(node,ast.Return):
                result=eval(compile(ast.Expression(node.value),"<risk-dsl>","eval"),{"__builtins__":{}},env); break
            if isinstance(node,(ast.Assign,ast.AnnAssign,ast.AugAssign,ast.If,ast.Expr)): exec(compile(ast.Module(body=[node],type_ignores=[]),"<risk-dsl>","exec"),{"__builtins__":{}},env)
            else: raise ValueError(f"unsupported top-level statement: {type(node).__name__}")
        return result

class DecisionEngine:
    """Decision runtime for visual rules and sandboxed Risk DSL with a canonical explainable contract."""
    def __init__(self): self.code=SafeCodeRunner(); self.formulas=FormulaEngine()
    def evaluate(self,facts:dict[str,Any],rules:list[DecisionRule],formulas:dict[str,str]|None=None)->dict[str,Any]:
        working=dict(facts); formula_trace=[]
        if formulas:
            calculated=self.formulas.evaluate(working,formulas); working=calculated["facts"]; formula_trace=calculated["trace"]
        triggered_rules=[]; actions=[]; trace=[]; reason_codes=[]
        for rule in rules:
            if not rule.enabled:
                trace.append({"rule_id":rule.id,"rule_name":rule.name,"status":"disabled"}); continue
            if getattr(rule,"execution_mode","visual")=="code":
                try: result=self.code.run(working,rule.code or "return None")
                except ValueError as exc:
                    trace.append({"rule_id":rule.id,"rule_name":rule.name,"status":"error","mode":"code","error":str(exc)}); continue
                matched=bool(result) if not isinstance(result,dict) else bool(result.get("matched",True))
                trace.append({"rule_id":rule.id,"rule_name":rule.name,"status":"triggered" if matched else "not_triggered","mode":"code","output":result})
                if matched:
                    triggered_rules.append(rule.id); actions.extend([{"rule_id":rule.id,"mode":rule.mode,**action.model_dump()} for action in rule.actions]); reason_codes.extend([f"CODE_{rule.id}"])
                continue
            results=[]
            for condition in rule.conditions:
                actual=working.get(condition.field); matched=self._compare(actual,condition.operator,condition.value)
                results.append({"field":condition.field,"operator":condition.operator,"expected":condition.value,"actual":actual,"matched":matched})
            logic=getattr(rule,"logic","AND") or "AND"
            if logic not in SUPPORTED_LOGIC: raise ValueError(f"Unsupported condition logic: {logic}")
            matched=all(x["matched"] for x in results) if logic=="AND" else any(x["matched"] for x in results)
            trace.append({"rule_id":rule.id,"rule_name":rule.name,"status":"triggered" if matched else "not_triggered","conditions":results,"logic":logic,"mode":rule.mode})
            if matched:
                triggered_rules.append(rule.id); actions.extend([{"rule_id":rule.id,"mode":rule.mode,**action.model_dump()} for action in rule.actions])
                for item in results:
                    if item["matched"]:
                        field=item["field"]
                        reason_codes.append({"par30":"PAR30_ABOVE_THRESHOLD","outstanding_balance":"EXPOSURE_MATERIAL","trend":"TREND_DETERIORATING","risk_score":"RISK_SCORE_POLICY_MATCH","priority_score":"PRIORITY_THRESHOLD"}.get(field,f"POLICY_{str(field).upper()}"))
        decision=None
        for action in actions:
            params=action.get("parameters") or {}
            if params.get("outcome") is not None: decision=params["outcome"]; break
        return {"decision":decision,"outcome":decision,"reason_codes":sorted(set(reason_codes)),"facts":working,"formula_trace":formula_trace,"triggered_rules":triggered_rules,"actions":actions,"evaluation_trace":trace}
    def normalize_rows(self,rows:list[dict[str,Any]],code:str)->list[dict[str,Any]]:
        output=[]
        for index,row in enumerate(rows):
            value=self.code.run(row,code)
            if not isinstance(value,dict): raise ValueError(f"row {index}: normalization code must return an object")
            output.append(value)
        return output
    @staticmethod
    def _compare(actual:Any,operator:str,expected:Any)->bool:
        if operator not in SUPPORTED_OPERATORS: raise ValueError(f"Unsupported operator: {operator}")
        if operator=="exists": return actual is not None
        if operator=="not_exists": return actual is None
        if actual is None: return operator in {"neq","not_in"}
        if operator=="eq": return actual==expected
        if operator=="neq": return actual!=expected
        if operator=="gt": return actual>expected
        if operator=="gte": return actual>=expected
        if operator=="lt": return actual<expected
        if operator=="lte": return actual<=expected
        if operator=="in": return actual in expected
        if operator=="not_in": return actual not in expected
        if operator=="between": return isinstance(expected,(list,tuple)) and len(expected)==2 and expected[0]<=actual<=expected[1]
        if operator=="contains": return expected in actual
        if operator=="not_contains": return expected not in actual
        return False
