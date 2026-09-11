from __future__ import annotations
from collections import defaultdict
from fastapi import APIRouter, HTTPException
from app.api.schemas import DecisionRule
from app.decision.rule_repository import DecisionRuleRepository
from app.engine.decision_engine import DecisionEngine
from app.engine.formula_engine import FormulaEngine
from app.engine.scorecard_engine import ScorecardEngine
from app.decision.rule_builder import RuleBuilder
from app.data.persistence import PortfolioPersistenceService

router=APIRouter(prefix="/v1/decision-builder",tags=["decision-builder"])
service=RuleBuilder(); engine=DecisionEngine(); formula_engine=FormulaEngine(); scorecard_engine=ScorecardEngine(); rules_repo=DecisionRuleRepository(); persistence=PortfolioPersistenceService()

def _prepare_facts(raw:dict, normalization:str|None, formulas:dict|None)->tuple[dict,list[str],list[dict]]:
    facts=dict(raw or {}); stages=[]; formula_trace=[]
    if normalization:
        errors=engine.code.validate(normalization)
        if errors: raise ValueError("; ".join(errors))
        facts=engine.normalize_rows([facts],normalization)[0]; stages.append("normalize")
    stages.append("facts")
    if formulas:
        calculated=formula_engine.evaluate(facts,formulas); facts=calculated["facts"]; formula_trace=calculated["trace"]; stages.append("formulas")
    return facts,stages,formula_trace

def _decision_result(facts:dict, decision_rule:DecisionRule, scorecard:dict|None)->tuple[dict,dict|None]:
    score_result=None
    if scorecard:
        score_result=scorecard_engine.evaluate(facts,scorecard); facts=score_result["facts"]
    result=engine.evaluate(facts,[decision_rule],None)
    result["policy_id"]=decision_rule.id; result["policy_version"]=decision_rule.version; result["scorecard"]=score_result
    return result,score_result

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
    try: facts,_,_=_prepare_facts(payload.get("facts",{}),None,compiled["compiled_rule"].get("formulas") or None); result,_=_decision_result(facts,rule,None)
    except (ValueError,TypeError) as exc: raise HTTPException(status_code=422,detail=[str(exc)])
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

@router.post("/pipeline")
def run_pipeline(payload:dict)->dict:
    rule=payload.get("rule")
    if not rule: raise HTTPException(status_code=422,detail=["rule is required"])
    compiled=compile_rule(rule)
    if not compiled["valid"]: raise HTTPException(status_code=422,detail=compiled["errors"])
    decision_rule=DecisionRule.model_validate(compiled["compiled_rule"])
    try:
        facts,stages,formula_trace=_prepare_facts(payload.get("facts",{}),payload.get("normalization_code"),payload.get("formulas") or None)
        scorecard_result=None
        if payload.get("scorecard"):
            scorecard_result=scorecard_engine.evaluate(facts,payload["scorecard"]); facts=scorecard_result["facts"]; stages.append("scorecard")
        result=engine.evaluate(facts,[decision_rule],None)
        result.update({"scorecard":scorecard_result,"formula_trace":formula_trace,"policy_id":decision_rule.id,"policy_version":decision_rule.version})
        stages.append("rules")
        if decision_rule.execution_mode=="code": stages.append("risk_dsl")
        stages.append("decision")
        return {"stages":stages,"facts":facts,"scorecard":scorecard_result,"result":result,"execution_mode":"test_only","customer_actions_executed":False}
    except (ValueError,TypeError) as exc: raise HTTPException(status_code=422,detail=[str(exc)])

def _baseline_decision(row:dict)->str|None:
    for key in ("baseline_decision","current_decision","decision","outcome","existing_decision"):
        value=row.get(key)
        if value not in (None,""): return str(value)
    return None

def _distribution(values:list[str])->dict[str,int]:
    out={}
    for value in values: out[value]=out.get(value,0)+1
    return out

def _outcome_value(row:dict,field:str|None)->str|None:
    if field:
        value=row.get(field)
        return None if value in (None,"") else str(value)
    for key in ("outcome","bad_flag","default_flag","defaulted","is_bad","bad","target","y_bad"):
        value=row.get(key)
        if value not in (None,""): return str(value)
    return None

def _is_bad(value:str|None)->bool|None:
    if value is None:return None
    v=str(value).strip().lower()
    if v in {"1","true","yes","y","bad","default","defaulted","delinquent","chargeoff","charged_off"}:return True
    if v in {"0","false","no","n","good","current","paid","performing","non_default"}:return False
    return None

@router.post("/portfolio-simulate")
def simulate_portfolio(payload:dict)->dict:
    rows=payload.get("rows") or []
    dataset_id=payload.get("dataset_id")
    if not rows and dataset_id: rows=persistence.portfolio_records.find({"dataset_id":dataset_id},limit=100000)
    rule=payload.get("rule"); scorecard=payload.get("scorecard"); normalization=payload.get("normalization_code"); formulas=payload.get("formulas") or None
    if not isinstance(rows,list) or not rows: raise HTTPException(status_code=422,detail=["rows must contain at least one record or provide a valid dataset_id"])
    if not isinstance(rule,dict): raise HTTPException(status_code=422,detail=["rule is required"])
    compiled=compile_rule(rule)
    if not compiled["valid"]: raise HTTPException(status_code=422,detail=compiled["errors"])
    decision_rule=DecisionRule.model_validate(compiled["compiled_rule"])
    if normalization:
        errors=engine.code.validate(normalization)
        if errors: raise HTTPException(status_code=422,detail=errors)
    results=[]; counts={}; bands={}; triggered={}; baseline_values=[]; transition_counts={}; total_exposure=0.0; exposure_by_decision={}; total_score=0.0; scored=0
    for index,row in enumerate(rows):
        try:
            raw=dict(row); baseline_decision=_baseline_decision(raw)
            if baseline_decision is not None: baseline_values.append(baseline_decision)
            facts,_,formula_trace=_prepare_facts(raw,normalization,formulas); score_result=None
            if scorecard: score_result=scorecard_engine.evaluate(facts,scorecard); facts=score_result["facts"]
            result=engine.evaluate(facts,[decision_rule],None); decision=result.get("decision") or result.get("outcome") or "NO_DECISION"; counts[decision]=counts.get(decision,0)+1
            if baseline_decision is not None:
                transition=f"{baseline_decision} → {decision}"; transition_counts[transition]=transition_counts.get(transition,0)+1
            band=(score_result or {}).get("band") or {}; label=band.get("label") if isinstance(band,dict) else None
            if label: bands[label]=bands.get(label,0)+1
            for rule_id in result.get("triggered_rules",[]): triggered[rule_id]=triggered.get(rule_id,0)+1
            try:
                exposure=float(facts.get("outstanding_balance",0) or 0); total_exposure+=exposure; exposure_by_decision[decision]=exposure_by_decision.get(decision,0)+exposure
            except (TypeError,ValueError): pass
            score=(score_result or {}).get("score")
            if score is not None: total_score+=float(score); scored+=1
            results.append({"index":index,"customer_id":facts.get("customer_id"),"baseline_decision":baseline_decision,"decision":decision,"score":score,"band":label,"triggered_rules":result.get("triggered_rules",[]),"reason_codes":result.get("reason_codes",[]),"formula_trace":formula_trace})
        except (ValueError,TypeError) as exc: raise HTTPException(status_code=422,detail=[f"row {index}: {exc}"])
    total=len(results); p=lambda d:round(d/total,4) if total else 0
    baseline_summary={"records":len(baseline_values),"decisions":_distribution(baseline_values),"decision_percentages":{k:p(v) for k,v in _distribution(baseline_values).items()},"available":bool(baseline_values)}
    return {"summary":{"records":total,"decisions":counts,"decision_percentages":{k:p(v) for k,v in counts.items()},"baseline":baseline_summary,"policy_transitions":transition_counts,"bands":bands,"band_percentages":{k:p(v) for k,v in bands.items()},"triggered_rules":triggered,"total_exposure":round(total_exposure,2),"exposure_by_decision":{k:round(v,2) for k,v in exposure_by_decision.items()},"average_score":round(total_score/scored,2) if scored else None,"scored_records":scored,"no_decision":counts.get("NO_DECISION",0),"decision_rate":round((total-counts.get("NO_DECISION",0))/total,4) if total else 0},"results":results,"policy":{"id":decision_rule.id,"name":decision_rule.name,"version":decision_rule.version},"dataset_id":dataset_id,"execution_mode":"portfolio_test_only","customer_actions_executed":False}

@router.post("/historical-replay")
def historical_replay(payload:dict)->dict:
    rows=payload.get("rows") or []
    dataset_id=payload.get("dataset_id")
    if not rows and dataset_id: rows=persistence.portfolio_records.find({"dataset_id":dataset_id},limit=100000)
    rule=payload.get("rule")
    if not isinstance(rows,list) or not rows: raise HTTPException(status_code=422,detail=["Historical replay requires rows or a valid dataset_id"])
    if not isinstance(rule,dict): raise HTTPException(status_code=422,detail=["rule is required"])
    compiled=compile_rule(rule)
    if not compiled["valid"]: raise HTTPException(status_code=422,detail=compiled["errors"])
    decision_rule=DecisionRule.model_validate(compiled["compiled_rule"])
    outcome_field=payload.get("outcome_field"); date_field=payload.get("date_field")
    replay=[]; transitions={}; outcome_rows=0; correct=0; incorrect=0; bad_total=0; bad_decisions=0; cuts=set()
    for index,row in enumerate(rows):
        raw=dict(row)
        if date_field and raw.get(date_field) is not None: cuts.add(str(raw.get(date_field)))
        elif raw.get("snapshot_date") is not None: cuts.add(str(raw.get("snapshot_date")))
        try:
            facts,_,_=_prepare_facts(raw,payload.get("normalization_code"),payload.get("formulas") or None)
            result=engine.evaluate(facts,[decision_rule],None)
        except (ValueError,TypeError) as exc: raise HTTPException(status_code=422,detail=[f"row {index}: {exc}"])
        decision=result.get("decision") or result.get("outcome") or "NO_DECISION"; observed=_baseline_decision(raw); outcome=_outcome_value(raw,outcome_field); bad=_is_bad(outcome)
        if observed is not None:
            key=f"{observed} → {decision}"; transitions[key]=transitions.get(key,0)+1
            if observed.strip().upper()==decision.strip().upper(): correct+=1
            else: incorrect+=1
        if bad is not None:
            outcome_rows+=1
            if bad: bad_total+=1
            if bad and decision.strip().upper() in {"REVIEW","DECLINE","BLOCK","HIGH_RISK","CRITICAL"}: bad_decisions+=1
        replay.append({"index":index,"customer_id":facts.get("customer_id"),"date":raw.get(date_field or "snapshot_date"),"observed_decision":observed,"policy_decision":decision,"outcome":outcome,"bad":bad,"triggered_rules":result.get("triggered_rules",[]),"reason_codes":result.get("reason_codes",[])})
    total=len(replay); decision_labeled=sum(transitions.values()); outcome_coverage=(outcome_rows/total) if total else 0
    accuracy=(correct/decision_labeled) if decision_labeled else None
    status="VALIDATED" if outcome_rows else ("REPLAY_WITH_DECISIONS" if decision_labeled else "REPLAY_ONLY")
    message=("Outcome labels available: policy can be compared with observed bad/good outcomes." if outcome_rows else "Historical replay completed; add an outcome/default field for predictive validation metrics.")
    return {"summary":{"records":total,"historical_cuts":len(cuts),"transitions":transitions,"decision_labeled_rows":decision_labeled,"correct":correct if decision_labeled else None,"incorrect":incorrect if decision_labeled else None,"accuracy":accuracy,"outcome_rows":outcome_rows,"outcome_coverage":outcome_coverage,"bad_rate":(bad_total/outcome_rows) if outcome_rows else None,"bad_rows":bad_total,"bad_decision_capture":(bad_decisions/bad_total) if bad_total else None,"validation_status":status,"validation_message":message},"results":replay,"policy":{"id":decision_rule.id,"name":decision_rule.name,"version":decision_rule.version},"dataset_id":dataset_id,"execution_mode":"historical_replay","customer_actions_executed":False}

@router.post("/normalize")
def normalize_rows(payload:dict)->dict:
    errors=engine.code.validate(payload.get("code",""))
    if errors: raise HTTPException(status_code=422,detail=errors)
    try: rows=engine.normalize_rows(payload.get("rows",[]),payload.get("code",""))
    except ValueError as exc: raise HTTPException(status_code=422,detail=[str(exc)])
    return {"rows":rows,"execution_mode":"sandboxed","customer_actions_executed":False}
