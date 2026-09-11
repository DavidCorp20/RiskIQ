import React from 'react'

const tone={critical:'CRÍTICA',high:'ALTA',medium:'MEDIA',low:'BAJA'}

function formatEvidence(evidence){
  if(Array.isArray(evidence))return evidence.join(' · ')
  return Object.entries(evidence||{}).map(([k,v])=>`${k}: ${typeof v==='object'?JSON.stringify(v):v}`).join(' · ')
}

export default function DecisionCenter({decisionEngine}){
  const engine=decisionEngine||{}
  const cards=Array.isArray(engine.cards)?engine.cards:[]
  return <section style={{marginTop:24,padding:20,border:'1px solid #e5e7eb',borderRadius:16,background:'#fff'}}>
    <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:12,marginBottom:16}}>
      <div><h2 style={{margin:0}}>Decision Center</h2><p style={{margin:'6px 0 0',color:'#6b7280'}}>Decisiones priorizadas por evidencia determinística. La ejecución requiere revisión humana.</p></div>
      <strong>{cards.length} decisión{cards.length===1?'':'es'}</strong>
    </div>
    {!cards.length?<div style={{padding:16,borderRadius:12,background:'#f9fafb'}}>No hay decisiones que requieran escalamiento con las reglas actuales.</div>:<div style={{display:'grid',gap:12}}>{cards.map(card=><article key={card.id} style={{padding:16,border:'1px solid #e5e7eb',borderRadius:12}}>
      <div style={{display:'flex',justifyContent:'space-between',gap:12}}><div><span style={{fontSize:12,fontWeight:700}}>P{card.priority} · {tone[card.severity]||String(card.severity||'').toUpperCase()}</span><h3 style={{margin:'6px 0'}}>{card.title}</h3></div><span style={{fontSize:12}}>Revisión humana</span></div>
      <p style={{margin:'8px 0'}}>{card.rationale}</p>
      <div style={{fontSize:13,color:'#4b5563'}}><strong>Evidencia:</strong> {formatEvidence(card.evidence)}</div>
      <div style={{marginTop:10,padding:10,borderRadius:8,background:'#f9fafb'}}><strong>Acción sugerida:</strong> {card.recommended_action}</div>
      <div style={{marginTop:10,fontSize:12,color:'#6b7280'}}>Estado: pendiente de revisión · Acción ejecutada: no</div>
    </article>)}</div>}
  </section>
}
