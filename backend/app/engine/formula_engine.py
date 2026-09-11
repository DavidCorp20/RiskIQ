from __future__ import annotations
import ast
from typing import Any
SAFE_FUNCTIONS={"abs":abs,"min":min,"max":max,"round":round,"len":len,"to_number":lambda x,default=0:_to_number(x,default),"to_text":lambda x:"" if x is None else str(x),"upper":lambda x:"" if x is None else str(x).upper(),"lower":lambda x:"" if x is None else str(x).lower(),"coalesce":lambda *xs:next((x for x in xs if x not in (None,"")),None)}
def _to_number(value:Any,default:float=0)->float:
    try:
        if value is None or value=="": return default
        return float(str(value).replace(",","."))
    except (TypeError,ValueError): return default
class FormulaEngine:
    """Safe expression engine for derived risk facts and scorecards."""
    ALLOWED=(ast.Expression,ast.Name,ast.Constant,ast.Dict,ast.List,ast.Tuple,ast.BinOp,ast.UnaryOp,ast.BoolOp,ast.Compare,ast.Add,ast.Sub,ast.Mult,ast.Div,ast.Mod,ast.Pow,ast.USub,ast.UAdd,ast.And,ast.Or,ast.Not,ast.Eq,ast.NotEq,ast.Gt,ast.GtE,ast.Lt,ast.LtE,ast.In,ast.NotIn,ast.Call,ast.keyword,ast.Subscript,ast.Load,ast.IfExp)
    def validate(self,expression:str)->list[str]:
        if not expression or not expression.strip(): return ["formula is required"]
        if len(expression)>4000: return ["formula exceeds 4,000 characters"]
        try: tree=ast.parse(expression,mode="eval")
        except SyntaxError as exc: return [f"syntax error: line {exc.lineno}: {exc.msg}"]
        errors=[]
        for node in ast.walk(tree):
            if not isinstance(node,self.ALLOWED): errors.append(f"unsupported construct: {type(node).__name__}")
            if isinstance(node,ast.Attribute): errors.append("attribute access is not allowed")
            if isinstance(node,ast.Call) and (not isinstance(node.func,ast.Name) or node.func.id not in SAFE_FUNCTIONS): errors.append("only approved helper functions can be called")
        return sorted(set(errors))
    def evaluate(self,facts:dict[str,Any],formulas:dict[str,str])->dict[str,Any]:
        env={**SAFE_FUNCTIONS,**facts}; trace=[]
        for name,expression in formulas.items():
            if not name or not name.replace("_","").isalnum() or name[0].isdigit(): raise ValueError(f"invalid formula name: {name}")
            errors=self.validate(expression)
            if errors: raise ValueError(f"{name}: {'; '.join(errors)}")
            value=eval(compile(ast.parse(expression,mode="eval"),"<risk-formula>","eval"),{"__builtins__":{}},env)
            env[name]=value; trace.append({"variable":name,"formula":expression,"value":value})
        return {"facts":{k:v for k,v in env.items() if k not in SAFE_FUNCTIONS},"trace":trace}
