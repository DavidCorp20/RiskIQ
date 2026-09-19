import React from 'react'
import ActionStatusBadge from './ActionStatusBadge'
const money=value=>Number(value||0).toLocaleString(undefined,{maximumFractionDigits:2})
export default function EvidenceDrawer({event,actions=[],onClose}){
 if(!event)return null
 const evidence=event.evidence||{}
 return <div className="risk-evidence-backdrop" onClick={onClose}>
  <aside className="risk-evidence-drawer" onClick={event=>event.stopPropagation()}>
   <header><div><span>IMMUTABLE RISK EVIDENCE</span><h3>{event.event_type||event.metric}</h3></div><button onClick={onClose} aria-label="Close evidence">×</button></header>
   <div className="risk-evidence-summary">
    <div><span>Severity</span><strong>{event.severity}</strong></div>
    <div><span>Observed</span><strong>{String(event.observed_value??'—')}</strong></div>
    <div><span>Exposure</span><strong>{'$'+money(event.exposure)}</strong></div>
   </div>
   <section><h4>Evidence</h4><pre>{JSON.stringify(evidence,null,2)}</pre></section>
   <section><h4>Actions</h4>{actions.length?actions.map(action=><div className="risk-evidence-action" key={action.action_id}><div><strong>{action.action_type}</strong><span>{action.owner}</span></div><ActionStatusBadge action={action}/></div>):<p>No action linked.</p>}</section>
  </aside>
 </div>
}