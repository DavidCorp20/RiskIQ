import React,{useEffect,useMemo,useState} from 'react'
import {AlertTriangle,CheckCircle2,ChevronRight,FileCheck2,Flag,ShieldAlert} from 'lucide-react'
import {listAuditDecisions} from './api'
import './decision-center.css'

const tone={critical:'CRÍTICA',high:'ALTA',medium:'MEDIA',low:'BAJA'}
const label=v=>String(v??'—').replaceAll('_',' ')
const fmt=v=>typeof v==='number'?v.toLocaleString(undefined,{maximumFractionDigits:4}):label(v)
function evidenceText(e){if(Array.isArray(e))return e.map(label).join(' · ');return Object.entries(e||{}).map(([k,v])=>`${k}: ${typeof v==='object'?JSON.stringify(v):v}`).join(' · ')}
function Panel({title,children}){return <div className="dc-panel"><div className="dc-panel-title">{title}</div>{children}</div>}

export default function DecisionCenter({decisionEngine,result,priorities=[],datasetId}){
 const source=result?.decision_engine||result?.decision||{}
 const engine=decisionEngine||source||{}
 const engineCards=Array.isArray(engine.cards)?engine.cards:Array.isArray(engine.priority_cards)?engine.priority_cards:[]
 const cards=engineCards.length?engineCards:(Array.isArray(priorities)?priorities:[])
 const evidence=engine.decision_evidence||source.decision_evidence||result?.decision_evidence||{}
 const [selected,setSelected]=useState(cards[0]||null)
 const [audit,setAudit]=useState([])
 const [auditLoading,setAuditLoading]=useState(false)
 const [auditError,setAuditError]=useState('')
 useEffect(()=>{if(!cards.length){setSelected(null);return}setSelected(prev=>prev&&cards.includes(prev)?prev:cards[0])},[cards.length])
 useEffect(()=>{let live=true;(async()=>{if(!datasetId){setAudit([]);return}setAuditLoading(true);setAuditError('');try{const data=await listAuditDecisions(datasetId);if(live)setAudit(data?.entries||[])}catch(e){if(live)setAuditError(e.message||'No se pudo cargar el ledger')}finally{if(live)setAuditLoading(false)}})();return()=>{live=false}},[datasetId])
 const selectedEvidence=selected?.evidence||evidence
 const facts=selectedEvidence?.facts||evidence.facts||{}
 const score=selectedEvidence?.scorecard?.score??evidence.scorecard?.score
 const drivers=engine.top_drivers||source.top_drivers||result?.analysis?.drivers||[]
 const path=engine.decision_path||source.decision_path||[]
 const stats=useMemo(()=>engine.counts||source.counts||{critical:cards.filter(x=>x.severity==='critical'||x.priority==='critical').length,high:cards.filter(x=>x.severity==='high'||x.priority==='high').length,watch:cards.filter(x=>!['critical','high'].includes(x.severity||x.priority)).length,total_cards:cards.length},[engine,source, cards.length])
 const policy=evidence.policy||selectedEvidence?.policy||{}
 return <section className="dc-shell">
  <header className="dc-header">
   <div><div className="dc-kicker">DECISION CENTER · MESA DE DECISIÓN</div><h2>Revisión institucional de decisiones</h2><p>La evidencia calculada se presenta para revisión humana. RiskIQ actúa como capa técnica de soporte: datos, variables, score, reglas y trazabilidad.</p></div>
   <div className="dc-header-status"><span>CASOS EN COLA</span><strong>{stats.total_cards||cards.length}</strong><small>requieren atención</small></div>
  </header>
  <div className="dc-kpis"><div><span>CRÍTICAS</span><strong>{stats.critical||0}</strong></div><div><span>ALTAS</span><strong>{stats.high||0}</strong></div><div><span>WATCH</span><strong>{stats.watch||0}</strong></div><div><span>HUMAN REVIEW</span><strong>ON</strong></div></div>
  {!cards.length?<div className="dc-empty"><strong>No hay decisiones para escalar.</strong><span>Ejecuta el análisis o ajusta la política para generar casos revisables.</span></div>:<div className="dc-layout">
   <div className="dc-list"><div className="dc-list-head"><span>DECISION QUEUE</span><b>{cards.length} casos</b></div><div className="dc-table-head"><span>Prioridad</span><span>Decisión / evidencia</span><span>Impacto</span><span>Estado</span><span>Acciones</span></div>{cards.map((card,i)=>{const priority=card.severity||card.priority||'watch';const impact=card.impact_score??card.estimated_impact??card.exposure_impact;const status=card.status||'PENDIENTE';return <button key={card.id||card.decision_id||i} className={`dc-case ${selected===card?'selected':''}`} onClick={()=>setSelected(card)}><div className="dc-case-priority"><span className={`dc-severity ${priority}`}>{tone[priority]||String(priority).toUpperCase()}</span><strong>#{card.rank??i+1}</strong></div><div className="dc-case-evidence"><strong>{card.title||card.name||card.decision_code||`Decisión ${i+1}`}</strong><small>{card.rationale||card.recommended_action||card.recommendation||'Revisión requerida'}</small><em>{evidenceText(card.evidence||{})||'Evidencia calculada disponible'}</em></div><div className="dc-case-impact"><strong>{impact==null?'—':fmt(impact)}</strong><small>impacto estimado</small></div><div className="dc-case-status"><span>{label(status).toUpperCase()}</span></div><div className="dc-case-actions"><span onClick={e=>{e.stopPropagation();setSelected(card)}}>Revisar</span><span className="disabled" title="Workflow de aprobación no ejecuta acciones externas">Aprobar</span><span className="disabled" title="Workflow de escalamiento no ejecuta acciones externas">Escalar</span></div><ChevronRight className="dc-case-chevron" size={15} strokeWidth={1.5}/></button>})}</div>
   <div className="dc-detail">
    <div className="dc-decision-hero"><div><span>DECISIÓN RESULTANTE</span><strong>{selectedEvidence?.decision||evidence.decision||selected?.recommended_action||selected?.recommendation||'REVIEW'}</strong><small>{selected?.rationale||'Decisión derivada de evidencia calculada.'}</small></div>{score!=null&&<div className="dc-score"><span>RISK SCORE</span><strong>{fmt(score)}</strong></div>}</div>
    <Panel title="DECISION PATH"><div className="dc-path">{path.length?path.map((step,i)=><React.Fragment key={`${step.stage||step.label}-${i}`}><div className="dc-step"><span>✓</span><b>{step.label}</b><small>{step.evidence==null?'Complete':fmt(step.evidence)}</small></div>{i<path.length-1&&<i className="dc-arrow">→</i>}</React.Fragment>):<div className="dc-muted">La ruta detallada estará disponible cuando el motor entregue el execution trace.</div>}</div></Panel>
    <div className="dc-two"><Panel title="INPUT & FACTS"><div className="dc-facts">{Object.entries(facts).slice(0,16).map(([k,v])=><div key={k}><span>{k}</span><b>{typeof v==='object'?JSON.stringify(v):fmt(v)}</b></div>)}</div>{!Object.keys(facts).length&&<div className="dc-muted">No se recibió un snapshot de facts para este caso.</div>}</Panel><Panel title="POLICY MATCH"><div className="dc-match"><div><span>TRIGGERED RULES</span><strong>{(selectedEvidence?.triggered_rules||evidence.triggered_rules||[]).length}</strong></div><div><span>REASON CODES</span><strong>{(selectedEvidence?.reason_codes||evidence.reason_codes||[]).length}</strong></div></div><p>{evidenceText(selectedEvidence?.reason_codes||evidence.reason_codes||selected?.evidence||{})||'La decisión no expone códigos de razón adicionales.'}</p></Panel></div>
    <Panel title="TOP RISK DRIVERS"><div className="dc-drivers">{drivers.slice(0,5).map((d,i)=><div key={i}><span>{d.title||d.name||d.segment||`Driver ${i+1}`}</span><b>{d.impact_score!=null?fmt(d.impact_score):'Evidence'}</b><small>{d.evidence||d.rationale||'Señal calculada'}</small></div>)}{!drivers.length&&<div className="dc-muted">Los drivers se mostrarán cuando el motor entregue evidencia de impacto.</div>}</div></Panel>
    <Panel title="DECISION EVIDENCE LEDGER"><div className="dc-drivers">{audit.slice(0,5).map((entry,i)=><div key={entry.decision_id||i}><span>{entry.decision_code||entry.title||'Decision'}</span><b>{label(entry.status)}</b><small>{new Date(entry.created_at).toLocaleString()} · {entry.policy_id?`Policy ${entry.policy_id}`:'Policy no identificada'}{entry.policy_version?` v${entry.policy_version}`:''}</small></div>)}{auditLoading&&<div className="dc-muted">Cargando evidencia persistida…</div>}{!auditLoading&&!audit.length&&!auditError&&<div className="dc-muted">No hay decisiones persistidas para esta cartera todavía.</div>}{auditError&&<div className="dc-muted">Ledger no disponible: {auditError}</div>}</div></Panel>
    <div className="dc-governance"><div><span>GOVERNANCE</span><strong>HUMAN REVIEW REQUIRED</strong><small>Acciones de cliente ejecutadas: NO · Causalidad inferida: NO</small></div><div><span>POLICY</span><strong>{policy.name||'—'} {policy.version?`v${policy.version}`:''}</strong><small>{policy.id||'Sin versión identificada'}</small></div></div>
    <details className="dc-technical"><summary>Evidence trace · técnico</summary><pre>{JSON.stringify({facts,scorecard:selectedEvidence?.scorecard||evidence.scorecard,triggered_rules:selectedEvidence?.triggered_rules||evidence.triggered_rules,reason_codes:selectedEvidence?.reason_codes||evidence.reason_codes,policy,ledger_count:audit.length},null,2)}</pre></details>
   </div>
  </div>}
 </section>
}
