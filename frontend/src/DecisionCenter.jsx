import React,{useMemo,useState} from 'react'
import './decision-center.css'

const tone={critical:'CRÍTICA',high:'ALTA',medium:'MEDIA',low:'BAJA'}
const label=v=>String(v??'—').replaceAll('_',' ')
const fmt=v=>typeof v==='number'?v.toLocaleString(undefined,{maximumFractionDigits:4}):label(v)
function evidenceText(e){if(Array.isArray(e))return e.map(label).join(' · ');return Object.entries(e||{}).map(([k,v])=>`${k}: ${typeof v==='object'?JSON.stringify(v):v}`).join(' · ')}
function Panel({title,children}){return <div className="dc-panel"><div className="dc-panel-title">{title}</div>{children}</div>}

export default function DecisionCenter({decisionEngine}){
 const engine=decisionEngine||{}
 const cards=Array.isArray(engine.cards)?engine.cards:Array.isArray(engine.priority_cards)?engine.priority_cards:[]
 const evidence=engine.decision_evidence||{}
 const [selected,setSelected]=useState(cards[0]||null)
 const selectedEvidence=selected?.evidence||evidence
 const facts=selectedEvidence?.facts||evidence.facts||{}
 const score=selectedEvidence?.scorecard?.score??evidence.scorecard?.score
 const drivers=engine.top_drivers||[]
 const path=engine.decision_path||[]
 const governance=engine.governance||{}
 const stats=useMemo(()=>engine.counts||{critical:0,high:0,watch:0,total_cards:cards.length},[engine, cards.length])
 return <section className="dc-shell">
  <header className="dc-header">
   <div><div className="dc-kicker">DECISION CENTER · EVIDENCE & EXPLAINABILITY</div><h2>Why did RiskIQ make this decision?</h2><p>Reconstrucción determinística del caso: datos, variables, score, reglas y decisión. Diseñado para revisión humana y auditoría.</p></div>
   <div className="dc-header-status"><span>DECISIONES</span><strong>{stats.total_cards||cards.length}</strong><small>requieren atención</small></div>
  </header>
  <div className="dc-kpis"><div><span>CRÍTICAS</span><strong>{stats.critical||0}</strong></div><div><span>ALTAS</span><strong>{stats.high||0}</strong></div><div><span>WATCH</span><strong>{stats.watch||0}</strong></div><div><span>HUMAN REVIEW</span><strong>ON</strong></div></div>
  {!cards.length?<div className="dc-empty"><strong>No hay decisiones para escalar.</strong><span>Ejecuta el análisis o ajusta la política para generar casos revisables.</span></div>:<div className="dc-layout">
   <div className="dc-list"><div className="dc-list-head"><span>QUEUE</span><b>{cards.length} casos</b></div>{cards.map((card,i)=><button key={card.id||i} className={`dc-case ${selected===card?'selected':''}`} onClick={()=>setSelected(card)}><div><span className={`dc-severity ${card.severity||card.priority||'watch'}`}>{tone[card.severity]||String(card.severity||card.priority||'WATCH').toUpperCase()}</span><strong>{card.title||card.name||`Decisión ${i+1}`}</strong><small>{card.rationale||card.recommended_action||'Revisión requerida'}</small></div><b>›</b></button>)}</div>
   <div className="dc-detail">
    <div className="dc-decision-hero"><div><span>DECISIÓN RESULTANTE</span><strong>{selectedEvidence?.decision||evidence.decision||selected?.recommended_action||'REVIEW'}</strong><small>{selected?.rationale||'Decisión derivada de evidencia calculada.'}</small></div>{score!=null&&<div className="dc-score"><span>RISK SCORE</span><strong>{fmt(score)}</strong></div>}</div>
    <Panel title="DECISION PATH"><div className="dc-path">{path.map((step,i)=><React.Fragment key={`${step.stage}-${i}`}><div className="dc-step"><span>✓</span><b>{step.label}</b><small>{step.evidence==null?'Complete':fmt(step.evidence)}</small></div>{i<path.length-1&&<i className="dc-arrow">→</i>}</React.Fragment>)}</div></Panel>
    <div className="dc-two"><Panel title="INPUT & FACTS"><div className="dc-facts">{Object.entries(facts).slice(0,16).map(([k,v])=><div key={k}><span>{k}</span><b>{typeof v==='object'?JSON.stringify(v):fmt(v)}</b></div>)}</div>{!Object.keys(facts).length&&<div className="dc-muted">No se recibió un snapshot de facts para este caso.</div>}</Panel><Panel title="POLICY MATCH"><div className="dc-match"><div><span>TRIGGERED RULES</span><strong>{(selectedEvidence?.triggered_rules||evidence.triggered_rules||[]).length}</strong></div><div><span>REASON CODES</span><strong>{(selectedEvidence?.reason_codes||evidence.reason_codes||[]).length}</strong></div></div><p>{evidenceText(selectedEvidence?.reason_codes||evidence.reason_codes||selected?.evidence||{})||'La decisión no expone códigos de razón adicionales.'}</p></Panel></div>
    <Panel title="TOP RISK DRIVERS"><div className="dc-drivers">{drivers.slice(0,5).map((d,i)=><div key={i}><span>{d.title||d.name||d.segment||`Driver ${i+1}`}</span><b>{d.impact_score!=null?fmt(d.impact_score):'Evidence'}</b><small>{d.evidence||d.rationale||'Señal calculada'}</small></div>)}{!drivers.length&&<div className="dc-muted">Los drivers se mostrarán cuando el motor entregue evidencia de impacto.</div>}</div></Panel>
    <div className="dc-governance"><div><span>GOVERNANCE</span><strong>HUMAN REVIEW REQUIRED</strong><small>Acciones de cliente ejecutadas: NO · Causalidad inferida: NO</small></div><div><span>POLICY</span><strong>{evidence.policy?.name||'—'} {evidence.policy?.version?`v${evidence.policy.version}`:''}</strong><small>{evidence.policy?.id||'Sin versión identificada'}</small></div></div>
    <details className="dc-technical"><summary>Evidence trace · técnico</summary><pre>{JSON.stringify({facts,scorecard:selectedEvidence?.scorecard||evidence.scorecard,triggered_rules:selectedEvidence?.triggered_rules||evidence.triggered_rules,reason_codes:selectedEvidence?.reason_codes||evidence.reason_codes,policy:evidence.policy},null,2)}</pre></details>
   </div>
  </div>}
 </section>
}
