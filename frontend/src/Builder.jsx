import {useEffect,useMemo,useState} from 'react'
import {evaluateDecisionRule,listDecisionRules,saveDecisionRule,validateDecisionRule} from './api'

const FIELDS=[
  ['par7','PAR7','ratio'],['par30','PAR30','ratio'],['par60','PAR60','ratio'],['par90','PAR90','ratio'],
  ['outstanding_balance','Exposición','money'],['active_loans','Créditos activos','number'],['days_past_due','Días de mora','number'],
  ['overdue_amount','Monto vencido','money'],['overdue_ratio','% vencido','ratio'],['score','Score','number'],
  ['segment','Segmento','text'],['product','Producto','text'],['region','Región','text'],['vintage','Antigüedad','number']
]
const OPERATORS=[['gt','>'],['gte','≥'],['lt','<'],['lte','≤'],['eq','='],['neq','≠'],['between','entre'],['contains','contiene'],['not_contains','no contiene'],['in','in'],['not_in','not in'],['exists','existe'],['not_exists','no existe']]
const ACTIONS=[['set_risk_level','Riesgo'],['review','Revisión'],['alert','Alerta'],['recommend','Recomendación'],['block','Bloquear']]
const MODES=[['suggested','Sugerida'],['manual','Manual'],['approval','Requiere aprobación'],['automatic','Automática']]
const newCondition=()=>({field:'par30',operator:'gt',value:8})
const initialRule=()=>({id:`rule-${Date.now()}`,name:'Mora crítica',conditions:[newCondition()],logic:'AND',mode:'suggested',enabled:true,actions:[{type:'set_risk_level',parameters:{level:'high'}},{type:'review',parameters:{reason:'Revisar cartera'}}]})

function displayValue(c){const meta=FIELDS.find(x=>x[0]===c.field)?.[2];if(meta==='ratio')return `${c.value}%`;if(meta==='money')return `$${Number(c.value||0).toLocaleString()}`;return c.value}
function toApiCondition(c){const meta=FIELDS.find(x=>x[0]===c.field)?.[2];let value=c.value;if(meta==='ratio'&&!['exists','not_exists'].includes(c.operator)){if(c.operator==='between'&&Array.isArray(value))value=value.map(v=>Number(v)/100);else value=Number(value)/100}return {...c,value}}

export default function Builder(){
 const [rule,setRule]=useState(initialRule)
 const [rules,setRules]=useState([])
 const [status,setStatus]=useState(null)
 const [loading,setLoading]=useState(false)
 const [facts,setFacts]=useState({par30:0.094,par90:0.012,outstanding_balance:25000,active_loans:180})
 const [testResult,setTestResult]=useState(null)
 const datasetId=useMemo(()=>{try{return JSON.parse(localStorage.getItem('riskiq.activeDataset')||'null')?.dataset_id||''}catch{return ''}},[])
 useEffect(()=>{listDecisionRules(datasetId).then(r=>setRules(r.items||[])).catch(()=>{})},[datasetId])
 const setCondition=(i,key,value)=>setRule(r=>({...r,conditions:r.conditions.map((c,j)=>j===i?{...c,[key]:value}:c)}))
 const addCondition=()=>setRule(r=>({...r,conditions:[...r.conditions,newCondition()]}))
 const removeCondition=i=>setRule(r=>({...r,conditions:r.conditions.filter((_,j)=>j!==i)}))
 const setAction=(i,key,value)=>setRule(r=>({...r,actions:r.actions.map((a,j)=>j===i?{...a,parameters:{...a.parameters,[key]:value}}:a)}))
 const addAction=()=>setRule(r=>({...r,actions:[...r.actions,{type:'review',parameters:{reason:'Revisar cartera'}}]}))
 const removeAction=i=>setRule(r=>({...r,actions:r.actions.filter((_,j)=>j!==i)}))
 const validate=async()=>{setLoading(true);setStatus(null);try{const r=await validateDecisionRule({...rule,conditions:rule.conditions.map(toApiCondition)});setStatus(r.valid?{kind:'ok',text:'Regla válida para el motor de decisión'}:{kind:'error',text:(r.errors||[]).join(' · ')})}catch(e){setStatus({kind:'error',text:e.message})}finally{setLoading(false)}}
 const save=async()=>{setLoading(true);setStatus(null);try{const r=await saveDecisionRule({...rule,conditions:rule.conditions.map(toApiCondition)},datasetId);setRules(x=>[r.rule,...x]);setStatus({kind:'ok',text:'Regla guardada y disponible para reutilizar'}); }catch(e){setStatus({kind:'error',text:e.message})}finally{setLoading(false)}}
 const test=async()=>{setLoading(true);setTestResult(null);try{const r=await evaluateDecisionRule({...rule,conditions:rule.conditions.map(toApiCondition)},facts);setTestResult(r.result);setStatus({kind:'ok',text:'Prueba ejecutada en modo seguro: no se ejecutan acciones sobre clientes'})}catch(e){setStatus({kind:'error',text:e.message})}finally{setLoading(false)}}
 return <div className="page-content builder-page">
  <div className="builder-header"><div><Section eyebrow="LOW-CODE DECISION ENGINE" title="Constructor de decisiones"/><p>Programa políticas de riesgo sin código. El motor evalúa evidencia determinística y deja la acción bajo control humano.</p></div><div className="builder-status"><span className="live-dot"/> MOTOR V2 · AUDITABLE</div></div>
  <div className="builder-layout">
   <main>
    <section className="builder-surface">
     <div className="builder-rule-head"><div><label>NOMBRE DE LA REGLA</label><input className="builder-name" value={rule.name} onChange={e=>setRule({...rule,name:e.target.value})}/></div><div><label>MODO DE EJECUCIÓN</label><select value={rule.mode} onChange={e=>setRule({...rule,mode:e.target.value})}>{MODES.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></div></div>
     <div className="builder-section"><div className="builder-section-title"><span>01</span><div><b>CUANDO</b><small>Condiciones que activan la regla</small></div><select value={rule.logic} onChange={e=>setRule({...rule,logic:e.target.value})}><option>AND</option><option>OR</option></select></div>
      {rule.conditions.map((c,i)=><div className="lowcode-row" key={i}><span className="node-index">{i+1}</span><select value={c.field} onChange={e=>setCondition(i,'field',e.target.value)}>{FIELDS.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select><select value={c.operator} onChange={e=>setCondition(i,'operator',e.target.value)}>{OPERATORS.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select>{['exists','not_exists'].includes(c.operator)?<div className="value-disabled">Sin valor</div>:c.operator==='between'?<div className="between-values"><input type="number" value={c.value?.[0]??0} onChange={e=>setCondition(i,'value',[e.target.value,c.value?.[1]??0])}/><span>y</span><input type="number" value={c.value?.[1]??0} onChange={e=>setCondition(i,'value',[c.value?.[0]??0,e.target.value])}/></div>:<input className="condition-value" value={c.value??''} onChange={e=>setCondition(i,'value',e.target.value)} />}{i>0&&<button className="icon-button" onClick={()=>removeCondition(i)}>×</button>}</div>)}
      <button className="builder-add" onClick={addCondition}>+ Añadir condición</button>
     </div>
     <div className="builder-connector"><span>{rule.logic}</span></div>
     <div className="builder-section"><div className="builder-section-title"><span>02</span><div><b>ENTONCES</b><small>Resultado que produce la regla</small></div></div>
      {rule.actions.map((a,i)=><div className="action-row" key={i}><select value={a.type} onChange={e=>setRule(r=>({...r,actions:r.actions.map((x,j)=>j===i?{type:e.target.value,parameters:{}}:x)}))}>{ACTIONS.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select>{a.type==='set_risk_level'&&<select value={a.parameters.level||'high'} onChange={e=>setAction(i,'level',e.target.value)}><option value="low">BAJO</option><option value="medium">MODERADO</option><option value="high">ALTO</option><option value="critical">CRÍTICO</option></select>}{a.type==='review'&&<input value={a.parameters.reason||''} onChange={e=>setAction(i,'reason',e.target.value)} placeholder="Motivo de revisión"/>}{a.type==='alert'&&<input value={a.parameters.message||''} onChange={e=>setAction(i,'message',e.target.value)} placeholder="Mensaje de alerta"/>}{a.type==='recommend'&&<input value={a.parameters.recommendation||''} onChange={e=>setAction(i,'recommendation',e.target.value)} placeholder="Recomendación"/>}{a.type==='block'&&<input value={a.parameters.reason||''} onChange={e=>setAction(i,'reason',e.target.value)} placeholder="Motivo de bloqueo"/>}{i>0&&<button className="icon-button" onClick={()=>removeAction(i)}>×</button>}</div>)}
      <button className="builder-add" onClick={addAction}>+ Añadir resultado</button>
     </div>
     <div className="builder-actions"><button className="secondary-button" onClick={validate} disabled={loading}>VALIDAR</button><button className="secondary-button" onClick={test} disabled={loading}>PROBAR REGLA</button><button className="primary-button" onClick={save} disabled={loading}>GUARDAR REGLA <span>↗</span></button></div>
     {status&&<div className={`builder-notice ${status.kind}`}>{status.kind==='ok'?'✓':'!'} {status.text}</div>}
    </section>
   </main>
   <aside className="builder-preview">
    <section className="preview-surface"><label>VISTA PREVIA</label><h3>{rule.name}</h3><div className="logic-preview">{rule.conditions.map((c,i)=><div key={i}><span>{FIELDS.find(x=>x[0]===c.field)?.[1]}</span><b>{OPERATORS.find(x=>x[0]===c.operator)?.[1]}</b><em>{displayValue(c)}</em>{i<rule.conditions.length-1&&<small>{rule.logic}</small>}</div>)}</div><div className="preview-arrow">↓</div><div className="outcome-list">{rule.actions.map((a,i)=><div key={i}><span>{i+1}</span><b>{ACTIONS.find(x=>x[0]===a.type)?.[1]}</b><em>{a.type==='set_risk_level'?(a.parameters.level||'high').toUpperCase():a.parameters.reason||a.parameters.message||a.parameters.recommendation||'Configurado'}</em></div>)}</div></section>
    <section className="preview-surface test-surface"><label>PRUEBA RÁPIDA</label><div className="fact-grid"><label>PAR30 %<input type="number" value={(facts.par30*100).toFixed(1)} onChange={e=>setFacts({...facts,par30:Number(e.target.value)/100})}/></label><label>PAR90 %<input type="number" value={(facts.par90*100).toFixed(1)} onChange={e=>setFacts({...facts,par90:Number(e.target.value)/100})}/></label><label>Exposición<input type="number" value={facts.outstanding_balance} onChange={e=>setFacts({...facts,outstanding_balance:Number(e.target.value)})}/></label><label>Créditos<input type="number" value={facts.active_loans} onChange={e=>setFacts({...facts,active_loans:Number(e.target.value)})}/></label></div>{testResult&&<div className="test-result"><b>{testResult.triggered_rules?.length?'REGLA ACTIVADA':'REGLA NO ACTIVADA'}</b><span>{testResult.actions?.length||0} resultado(s) · {testResult.evaluation_trace?.length||0} evidencias evaluadas</span></div>}</section>
    <section className="preview-surface"><label>REGLAS GUARDADAS</label>{rules.length?<div className="saved-rules">{rules.slice(0,5).map((r,i)=><button key={i} onClick={()=>setRule({...r})}><b>{r.name}</b><span>{r.mode||'suggested'} · {r.conditions?.length||0} condiciones</span></button>)}</div>:<p className="muted-block">Aún no hay reglas reutilizables para este dataset.</p>}</section>
   </aside>
  </div>
 </div>
}
function Section({eyebrow,title}){return <div className="section-head builder-section-head"><div><span className="section-eyebrow">{eyebrow}</span><h2>{title}</h2></div></div>}
