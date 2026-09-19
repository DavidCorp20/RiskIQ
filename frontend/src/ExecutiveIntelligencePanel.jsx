import React,{useMemo,useState} from 'react'
import { runStressScenario } from './api'
export default function ExecutiveIntelligencePanel({intelligence}) {
 const [scenario,setScenario]=useState('BASE'),[stress,setStress]=useState(null),[loading,setLoading]=useState(false)
 const events=intelligence?.risk_events?.events||[]
 const ratings=intelligence?.predictive?.pd_ratings||[]
 const heat=useMemo(()=>['CRITICAL','HIGH','MEDIUM','LOW'].map(severity=>({severity,count:events.filter(e=>e.severity===severity).length})),[events])
 const run=async next=>{setScenario(next);setLoading(true);try{setStress(await runStressScenario(intelligence?.stress_testing?.baseline||{},next,{}))}finally{setLoading(false)}}
 return <section className="ri-exec-panel" style={{marginTop:16}}>
  <div className="ri-exec-panel-head"><div><span>EXECUTIVE INTELLIGENCE</span><h3>Predictive, events & stress</h3></div><b>{intelligence?.evidence_hash?'GROUNDED':'WAITING'}</b></div>
  <div className="ri-exec-grid ri-exec-mini">
   <article><span>PD ratings</span><strong>{ratings.length}</strong></article>
   <article><span>Risk events</span><strong>{events.length}</strong></article>
   <article><span>Evidence hash</span><strong>{intelligence?.evidence_hash?'OK':'—'}</strong></article>
  </div>
  <div className="ri-exec-grid ri-exec-mini" style={{marginTop:12}}>{heat.map(item=><article key={item.severity}><span>{item.severity}</span><strong>{item.count}</strong></article>)}</div>
  <div style={{display:'flex',gap:8,marginTop:14,alignItems:'center'}}><span>Stress scenario</span>{['BASE','ADVERSE','SEVERE_STRESS'].map(x=><button key={x} onClick={()=>run(x)} disabled={loading} className={scenario===x?'active':''}>{x}</button>)}</div>
  {stress&&<p className="ri-exec-muted">Scenario {stress.scenario}: projection is deterministic and only applies validated sensitivities. Without validated elasticities, metrics remain at baseline.</p>}
 </section>
}
