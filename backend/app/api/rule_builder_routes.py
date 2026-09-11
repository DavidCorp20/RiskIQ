from __future__ import annotations
from fastapi import APIRouter, HTTPException
from app.api.schemas import DecisionRule
from app.decision.rule_repository import DecisionRuleRepository
from app.engine.decision_engine import DecisionEngine
from app.engine.formula_engine import FormulaEngine
from app.engine.scorecard_engine import ScorecardEngine
from app.decision.rule_builder import RuleBuilder

router=APIRouter(prefix="/v1/decision-builder",tags=["decision-builder"])
service=RuleBuilder(); engine=DecisionEngine(); formula_engine=FormulaEngine(); scorecard_engine=ScorecardEngine(); rules_repo=DecisionRuleRepository()

@router.get("/rules")
def list_rules(dataset_id:str|None=None,business_id:str|None=None)->dict:
    return {"items":rules_repo.list(dataset_id=dataset_id,business_id=business_id)}

@router.post("/validate")
def validate_rule(payload:dict)->dict:
    result=service.compile(payload)
    if payload.get("execution_mode")=="code": result["errors"]+=engine.code.validate(payload.get("code","")); result["valid"]=not result["errors"]
    if payload.get("execution_mode")=="formula":
        for expr in payload.get("formulas",{}).values(): result["errors"]+=formula_engine.validate(expr)
        result["valid"]=not result["errors"]
    return result

@router.post("/compile")
def compile_rule(payload:dict)->dict:
    result=validate_rule(payload)
    if result["valid"]: result["compiled_rule"]=dict(result["compiled_rule"],builder_version="5.0",contract="riskiq-decision-engine")
    return result

@router.post("/save")
def save_rule(payload:dict)->dict:
    compiled=compile_rule(payload.get("rule",payload))
    if not compiled["valid"]: raise HTTPException(status_code=422,detail=compiled["errors"])
    saved=rules_repo.save(compiled["compiled_rule"],payload.get("dataset_id"),payload.get("business_id")); return {"saved":True,"rule":saved}

@router.post("/evaluate")
def evaluate_rule(payload:dict)->dict:
    compiled=compile_rule(payload.get("rule",{}))
    if not compiled["valid"]: raise HTTPException(status_code=422,detail=compiled["errors"])
    rule=DecisionRule.model_validate(compiled["compiled_rule"])
    result=engine.evaluate(payload.get("facts",{}),[rule],compiled["compiled_rule"].get("formulas") or None)
    return {"compiled_rule":compiled["compiled_rule"],"result":result,"execution_mode":"test_only","customer_actions_executed":False}

@router.post("/formula")
def evaluate_formulas(payload:dict)->dict:
    formulas=payload.get("formulas",{})
    if not isinstance(formulas,dict) or not formulas: raise HTTPException(status_code=422,detail=["formulas object is required"])
    try: result=formula_engine.evaluate(payload.get("facts",{}),formulas)
    except ValueError as exc: raise HTTPException(status_code=422,detail=[str(exc)])
    return {**result,"execution_mode":"sandboxed","customer_actions_executed":False}

@router.post("/scorecard/validate")
def validate_scorecard(payload:dict)->dict:
    errors=scorecard_engine.validate(payload.get("scorecard",payload)); return {"valid":not errors,"errors":errors}

@router.post("/scorecard/evaluate")
def evaluate_scorecard(payload:dict)->dict:
    try: result=scorecard_engine.evaluate(payload.get("facts",{}),payload.get("scorecard",{}))
    except ValueError as exc: raise HTTPException(status_code=422,detail=[str(exc)])
    return {"result":result,"execution_mode":"sandboxed","customer_actions_executed":False}

def _calculate_facts(raw_facts:dict,normalization:str|None,formulas:dict|None)->tuple[dict,list[dict]]:
    facts=dict(raw_facts); trace=[]
    if normalization:
        errors=engine.code.validate(normalization)
        if errors: raise ValueError("; ".join(errors))
        facts=engine.normalize_rows([facts],normalization)[0]
    if formulas:
        calculated=formula_engine.evaluate(facts,formulas); facts=calculated["facts"]; trace=calculated["trace"]
    return facts,trace

@router.post("/pipeline")
def run_pipeline(payload:dict)->dict:
    facts=dict(payload.get("facts",{})); normalization=payload.get("normalization_code"); formulas=payload.get("formulas") or None; stages=[]; formula_trace=[]
    try:
        facts,formula_trace=_calculate_facts(facts,normalization,formulas)
    except ValueError as exc: raise HTTPException(status_code=422,detail=[str(exc)])
    if normalization: stages.append("normalize")
    stages.append("facts")
    if formulas: stages.append("formulas")
    scorecard=payload.get("scorecard"); scorecard_result=None
    if scorecard:
        try: scorecard_result=scorecard_engine.evaluate(facts,scorecard); facts=scorecard_result["facts"]; stages.append("scorecard")
        except ValueError as exc: raise HTTPException(status_code=422,detail=[str(exc)])
    rule=payload.get("rule")
    if not rule: raise HTTPException(status_code=422,detail=["rule is required"])
    compiled=compile_rule(rule)
    if not compiled["valid"]: raise HTTPException(status_code=422,detail=compiled["errors"])
    result=engine.evaluate(facts,[DecisionRule.model_validate(compiled["compiled_rule"])])
    stages += ["logic","decision"]
    return {"stages":stages,"facts":facts,"formula_trace":formula_trace,"scorecard":scorecard_result,"result":result,"execution_mode":"test_only","customer_actions_executed":False}

@router.post("/portfolio-simulate")
def simulate_portfolio(payload:dict)->dict:
    rows=payload.get("rows",[]); rule=payload.get("rule"); scorecard=payload.get("scorecard"); normalization=payload.get("normalization_code"); formulas=payload.get("formulas") or None
    if not isinstance(rows,list) or not rows: raise HTTPException(status_code=422,detail=["rows must contain at least one record"])
    if not isinstance(rule,dict): raise HTTPException(status_code=422,detail=["rule is required"])
    compiled=compile_rule(rule)
    if not compiled["valid"]: raise HTTPException(status_code=422,detail=compiled["errors"])
    decision_rule=DecisionRule.model_validate(compiled["compiled_rule"])
    if normalization:
        errors=engine.code.validate(normalization)
        if errors: raise HTTPException(status_code=422,detail=errors)
    results=[]; counts={}; bands={}; triggered={}; total_exposure=0.0; scores=[]
    for index,row in enumerate(rows):
        try:
            facts,formula_trace=_calculate_facts(row,normalization,formulas)
            score_result=None
            if scorecard:
                score_result=scorecard_engine.evaluate(facts,scorecard); facts=score_result["facts"]
            result=engine.evaluate(facts,[decision_rule])
            decision=result.get("decision") or "NO_DECISION"; counts[decision]=counts.get(decision,0)+1
            band=(score_result or {}).get("band") or {}; label=band.get("label") if isinstance(band,dict) else None
            if label: bands[label]=bands.get(label,0)+1
            for rule_id in result.get("triggered_rules",[]): triggered[rule_id]=triggered.get(rule_id,0)+1
            score=(score_result or {}).get("score")
            if isinstance(score,(int,float)): scores.append(float(score))
            try: total_exposure+=float(facts.get("outstanding_balance",0) or 0)
            except (TypeError,ValueError): pass
            results.append({"index":index,"customer_id":facts.get("customer_id"),"decision":decision,"score":score,"band":label,"triggered_rules":result.get("triggered_rules",[]),"reason_codes":result.get("reason_codes",[]),"formula_trace":formula_trace})
        except (ValueError,TypeError) as exc:
            raise HTTPException(status_code=422,detail=[f"row {index}: {exc}"])
    total=len(results); decision_share={k:round(v/total,4) for k,v in counts.items()} if total else {}
    return {"summary":{"records":total,"decisions":counts,"decision_share":decision_share,"bands":bands,"triggered_rules":triggered,"total_exposure":round(total_exposure,2),"average_score":round(sum(scores)/len(scores),2) if scores else None,"scored_records":len(scores)},"results":results,"policy":{"id":decision_rule.id,"name":decision_rule.name,"version":decision_rule.version},"execution_mode":"portfolio_test_only","customer_actions_executed":False}

@router.post("/normalize")
def normalize_rows(payload:dict)->dict:
    errors=engine.code.validate(payload.get("code",""))
    if errors: raise HTTPException(status_code=422,detail=errors)
    try: rows=engine.normalize_rows(payload.get("rows",[]),payload.get("code",""))
    except ValueError as exc: raise HTTPException(status_code=422,detail=[str(exc)])
    return {"rows":rows,"execution_mode":"sandboxed","customer_actions_executed":False}
