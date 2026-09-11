import React,{useEffect,useMemo,useState} from 'react'
import {listDatasets,listDecisionRules,simulateDecisionBacktest} from './api'

const readActive=()=>{try{return JSON.parse(localStorage.getItem('riskiq.activeDataset')||'null')?.dataset_id||''}catch{return ''}}
const pct=(v,total)=>total?`${((Number(v||0)/total)*100).toFixed(1)}%`:'0.0%'

export default function PolicyBacktest(){
 const [datasets,setDatasets]=useState([]),[datasetId,setDatasetId]=useState(readActive()),[rules,setRules]=useState([]),[ruleId,setRuleId]=useState(''),[result,setResult]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const selectedRule=useMemo(()=>rules.find(r=>r.id===ruleId)||rules[0]||null,[rules,ruleId])
 useEffect(()=>{listDatasets().then(r=>{const x=r?.datasets||r?.items||[];setDatasets(x);if(!datasetId&&x[0])setDatasetId(x[0].dataset_id||x[0].id)}).catch(()=>{})},[])
 useEffect(()=>{if(!datasetId){setRules([]);return}listDecisionRules(datasetId).then(r=>{const x=r?.items||[];setRules(x);setRuleId(x[0]?.id||'')}).catch(()=>setRules([]))},[datasetId])
 const run=async()=>{if(!datasetId||!selectedRule)return;setBusy(true);setError('');try{setResult(await simulateDecisionBacktest({dataset_id:datasetId,rule:selectedRule}))}catch(e){setError(e?.message||'Backtest failed')}finally{setBusy(false)}}
 const s=result?.summary||{}
 return <section className="ri-backtest-shell">
  <div className="ri-backtest-head"><div><div className="ri-kicker">POLICY BACKTEST · HISTORICAL REPLAY</div><h2>What would this policy have done?</h2><p>Replay a saved policy against historical portfolio observations. This is validation evidence, not a causal forecast.</p></div><span className="ri-chip">REPLAY · NO ACTIONS</span></div>
  <div className="ri-backtest-toolbar"><label>DATASET<select value={datasetId} onChange={e=>{setDatasetId(e.target.value);setResult(null)}}><option value="">Select dataset…</option>{datasets.map(d=><option key={d.dataset_id||d.id} value={d.dataset_id||d.id}>{d.source_name||d.name||d.dataset_id}</option>)}</select></label><label>POLICY<select value={selectedRule?.id||''} onChange={e=>setRuleId(e.target.value)}><option value="">Select saved policy…</option>{rules.map(r=><option key={r.id} value={r.id}>{r.name} · v{r.version||1}</option>)}</select></label><button className="ri-btn ri-btn-primary" disabled={busy||!selectedRule} onClick={run}>{busy?'Replaying…':'Run backtest'}</button></div>
  {error&&<div className="ri-backtest-error">{error}</div>}
  {!result?<div className="ri-backtest-empty"><strong>Historical replay is ready.</strong><span>Select a dataset and a saved policy. RiskIQ will group observations by historical cut when date information is available and compare the policy decision with observed outcomes when an outcome field exists.</span></div>:<>
   <div className="ri-backtest-kpis"><div><span>OBSERVATIONS</span><strong>{Number(s.records||0).toLocaleString()}</strong></div><div><span>OUTCOME COVERAGE</span><strong>{s.outcome_coverage==null?'—':`${(Number(s.outcome_coverage)*100).toFixed(1)}%`}</strong></div><div><span>ACCURACY</span><strong>{s.accuracy==null?'—':`${(Number(s.accuracy)*100).toFixed(1)}%`}</strong></div><div><span>BAD RATE</span><strong>{s.bad_rate==null?'—':`${(Number(s.bad_rate)*100).toFixed(1)}%`}</strong></div></div>
   <div className="ri-backtest-grid"><div className="ri-panel"><div className="ri-panel-head"><div><div className="ri-eyebrow">Decision replay</div><h3>Policy vs observed decision</h3></div></div>{Object.entries(s.transitions||{}).slice(0,10).map(([k,v])=><div className="ri-impact-line" key={k}><span>{k}</span><b>{Number(v).toLocaleString()}</b><em>{pct(v,s.records)}</em></div>)}{!Object.keys(s.transitions||{}).length&&<div className="ri-empty-score"><span>No historical decision labels were found.</span></div>}</div><div className="ri-panel"><div className="ri-panel-head"><div><div className="ri-eyebrow">Outcome evidence</div><h3>Validation status</h3></div></div><div className="ri-validation-state"><strong>{s.validation_status||'REPLAY_ONLY'}</strong><span>{s.validation_message||'Historical replay completed without outcome validation.'}</span></div><div className="ri-context-grid"><div><span>Historical cuts</span><b>{s.historical_cuts||0}</b></div><div><span>Outcome rows</span><b>{s.outcome_rows||0}</b></div><div><span>Correct</span><b>{s.correct==null?'—':s.correct}</b></div><div><span>Incorrect</span><b>{s.incorrect==null?'—':s.incorrect}</b></div></div></div></div>
   <details className="ri-technical"><summary>Replay evidence · row-level results</summary><pre>{JSON.stringify({summary:s,policy:result.policy,dataset_id:result.dataset_id,results:(result.results||[]).slice(0,100)},null,2)}</pre></details>
  </>}
 </section>
}
