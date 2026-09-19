import React,{useEffect,useMemo,useState} from 'react'
import {CheckCircle2,ChevronRight,RefreshCw,ShieldAlert,XCircle} from 'lucide-react'
import {
  approveDecision,
  createDecisionRecommendation,
  getDecisionLedger,
  rejectDecision
} from './api'
import {useRiskIntelligence} from './RiskIntelligenceProvider'
import './decision-center.css'
import './step7-governance.css'

const levelLabel={high:'ALTA',medium:'MEDIA',low:'BAJA'}
const levelTone={high:'critical',medium:'high',low:'low'}

const money=v=>typeof v==='number'
  ? '$'+v.toLocaleString(undefined,{maximumFractionDigits:2})
  : v == null || v === '' ? '—' : String(v)

const formatValue=v=>{
  if(v == null || v === '') return '—'
  if(typeof v === 'number') return v.toLocaleString(undefined,{maximumFractionDigits:4})
  if(typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

function evidenceEntries(value){
  if(Array.isArray(value)) return value.map((item,i)=>[String(i+1),item])
  return Object.entries(value || {})
}

function severityRank(item){
  return item?.action_level==='high'?0:item?.action_level==='medium'?1:2
}

export default function DecisionCenter(){
  const {
    dataset,
    result,
    decisionRecommendations,
    decisionLoading,
    decisionError,
    refreshDecisionRecommendations
  }=useRiskIntelligence()

  const [selectedId,setSelectedId]=useState('')
  const [ledger,setLedger]=useState([])
  const [ledgerLoading,setLedgerLoading]=useState(false)
  const [ledgerError,setLedgerError]=useState('')
  const [generating,setGenerating]=useState(false)
  const [reviewing,setReviewing]=useState(false)
  const [reviewComment,setReviewComment]=useState('')
  const [reviewError,setReviewError]=useState('')
  const [notice,setNotice]=useState('')

  const cards=useMemo(
    ()=>[...(decisionRecommendations||[])].sort((a,b)=>severityRank(a)-severityRank(b)||String(b.created_at||'').localeCompare(String(a.created_at||''))),
    [decisionRecommendations]
  )
  const selected=cards.find(item=>item.recommendation_id===selectedId)||cards[0]||null

  useEffect(()=>{
    if(!selected){
      setSelectedId('')
      setLedger([])
      return
    }
    if(selected.recommendation_id!==selectedId) setSelectedId(selected.recommendation_id)
  },[selected,selectedId])

  useEffect(()=>{
    let live=true
    ;(async()=>{
      if(!selected?.recommendation_id){setLedger([]);return}
      setLedgerLoading(true)
      setLedgerError('')
      try{
        const response=await getDecisionLedger({
          dataset_id:dataset?.dataset_id,
          recommendation_id:selected.recommendation_id,
          limit:50
        })
        if(live) setLedger(response?.items||[])
      }catch(e){
        if(live) setLedgerError(e.message||'No se pudo cargar el ledger')
      }finally{
        if(live) setLedgerLoading(false)
      }
    })()
    return()=>{live=false}
  },[selected?.recommendation_id,dataset?.dataset_id])

  const generate=async()=>{
    if(!dataset?.dataset_id) return
    setGenerating(true);setNotice('');setReviewError('')
    try{
      await createDecisionRecommendation({
        dataset_id:dataset.dataset_id,
        risk_facts:result?.risk_facts||{},
      })
      await refreshDecisionRecommendations(dataset.dataset_id)
      setNotice('Recomendaciones determinísticas actualizadas.')
    }catch(e){
      setNotice(e.message||'No se pudieron generar recomendaciones.')
    }finally{setGenerating(false)}
  }

  const review=async status=>{
    if(!selected?.recommendation_id) return
    const comment=reviewComment.trim()
    if(!comment){
      setReviewError('La justificación es obligatoria para aprobar o rechazar.')
      return
    }
    setReviewing(true);setReviewError('');setNotice('')
    try{
      if(status==='approved'){
        await approveDecision(selected.recommendation_id,{comment,actor:'user'})
      }else{
        await rejectDecision(selected.recommendation_id,{comment,actor:'user'})
      }
      await refreshDecisionRecommendations(dataset?.dataset_id)
      setReviewComment('')
      setNotice(status==='approved'
        ? 'Recomendación aprobada y registrada en el ledger.'
        : 'Recomendación rechazada y registrada en el ledger.')
    }catch(e){
      setReviewError(e.message||'No se pudo actualizar la recomendación.')
    }finally{setReviewing(false)}
  }

  const counts={
    high:cards.filter(x=>x.action_level==='high').length,
    medium:cards.filter(x=>x.action_level==='medium').length,
    low:cards.filter(x=>x.action_level==='low').length,
    pending:cards.filter(x=>['pending_approval','proposed'].includes(x.status)).length
  }

  return <section className="dc-shell">
    <header className="dc-header">
      <div>
        <div className="dc-kicker">DECISION CENTER · HUMAN GOVERNANCE</div>
        <h2>Recomendaciones de riesgo</h2>
        <p>
          La bandeja se alimenta de políticas determinísticas. Cada recomendación conserva
          su evidencia congelada y ninguna acción sobre clientes se ejecuta automáticamente.
        </p>
      </div>
      <div className="dc-header-status">
        <span>REVISIÓN PENDIENTE</span>
        <strong>{counts.pending}</strong>
        <small>{dataset?.source_name||'Cartera activa'}</small>
      </div>
    </header>

    <div className="dc-kpis">
      <div><span>HIGH</span><strong>{counts.high}</strong></div>
      <div><span>MEDIUM</span><strong>{counts.medium}</strong></div>
      <div><span>LOW</span><strong>{counts.low}</strong></div>
      <div><span>HUMAN REVIEW</span><strong>ON</strong></div>
    </div>

    <div className="dc-toolbar">
      <div>
        <span className="dc-method-badge"><ShieldAlert size={13}/> DETERMINISTIC POLICY</span>
        <span className="dc-toolbar-copy">EWS → política v{selected?.policy_version||1} → recomendación → revisión humana</span>
      </div>
      <button className="dc-refresh" onClick={generate} disabled={!dataset||generating}>
        <RefreshCw size={14} className={generating?'dc-spin':''}/>
        {generating?'Generando…':'Generar / actualizar recomendaciones'}
      </button>
    </div>

    {notice&&<div className="dc-notice">{notice}</div>}
    {decisionError&&<div className="dc-notice error">{decisionError}</div>}

    {decisionLoading?<div className="dc-empty"><strong>Cargando recomendaciones…</strong></div>:
      !cards.length?<div className="dc-empty">
        <strong>No hay recomendaciones persistidas para esta cartera.</strong>
        <span>Ejecuta el generador determinístico para crear la bandeja de revisión.</span>
      </div>:
      <div className="dc-layout">
        <div className="dc-list">
          <div className="dc-list-head"><span>RECOMMENDATION QUEUE</span><b>{cards.length} casos</b></div>
          {cards.map((card,i)=>{
            const selectedRow=selected?.recommendation_id===card.recommendation_id
            const requiresReview=card.requires_human_approval
            return <button
              key={card.recommendation_id}
              className={'dc-case '+(selectedRow?'selected':'')}
              onClick={()=>setSelectedId(card.recommendation_id)}
            >
              <div className="dc-case-priority">
                <span className={'dc-severity '+levelTone[card.action_level]}>{levelLabel[card.action_level]||card.action_level}</span>
                <strong>#{i+1}</strong>
              </div>
              <div className="dc-case-evidence">
                <strong>{card.action?.replaceAll('_',' ')||'REVIEW'}</strong>
                <small>{card.rationale||'Recomendación basada en evidencia EWS.'}</small>
                <em>{(card.trigger_codes||[]).join(' · ')||'Evidencia determinística disponible'}</em>
              </div>
              <div className="dc-case-impact">
                <strong>{card.loan_id||'Cartera'}</strong>
                <small>{requiresReview?'Aprobación requerida':'Solo revisión'}</small>
              </div>
              <div className="dc-case-status"><span>{String(card.status||'proposed').replaceAll('_',' ').toUpperCase()}</span></div>
              <div className="dc-case-actions">
                <span>Revisar</span>
              </div>
              <ChevronRight className="dc-case-chevron" size={15}/>
            </button>
          })}
        </div>

        <div className="dc-detail">
          <div className="dc-decision-hero">
            <div>
              <span>RECOMENDACIÓN</span>
              <strong>{selected.action?.replaceAll('_',' ').toUpperCase()}</strong>
              <small>{selected.rationale}</small>
            </div>
            <div className="dc-score">
              <span>POLICY</span>
              <strong>v{selected.policy_version}</strong>
            </div>
          </div>

          <Panel title="EVIDENCIA CONGELADA">
            <div className="dc-facts">
              {evidenceEntries(selected.evidence).map(([key,value])=>
                <div key={key}><span>{key.replaceAll('_',' ')}</span><b>{formatValue(value)}</b></div>
              )}
            </div>
            <div className="dc-ledger-meta">
              <span>HASH</span>
              <code>{selected.evidence_hash||'—'}</code>
              <span>AS OF</span>
              <code>{selected.evidence?.portfolio_as_of||selected.created_at||'—'}</code>
            </div>
          </Panel>

          <Panel title="IMMUTABLE DECISION LEDGER">
            {ledgerLoading?<div className="dc-muted">Cargando snapshots…</div>:
              ledgerError?<div className="dc-muted">Ledger no disponible: {ledgerError}</div>:
              ledger.length?ledger.map(entry=><div className="dc-ledger-row" key={entry.ledger_id}>
                <div><b>{entry.event}</b><span>{entry.state}</span></div>
                <small>{new Date(entry.created_at).toLocaleString()} · {entry.actor}</small>
                <code>{entry.evidence_hash}</code>
              </div>):
              <div className="dc-muted">No hay eventos de ledger para esta recomendación.</div>}
          </Panel>

          <Panel title="GUARDRAILS">
            <div className="dc-governance">
              <div><span>METHOD</span><strong>DETERMINISTIC EWS</strong><small>La política calcula; la IA no ejecuta.</small></div>
              <div><span>CAUSALITY</span><strong>NOT INFERRED</strong><small>La evidencia no demuestra causalidad por sí sola.</small></div>
              <div><span>ACTIONS</span><strong>NO CUSTOMER ACTIONS</strong><small>Aprobar no ejecuta acciones externas.</small></div>
              <div><span>APPROVAL</span><strong>{selected.requires_human_approval?'REQUIRED':'NOT REQUIRED'}</strong><small>Medium/High requieren revisión humana.</small></div>
            </div>
          </Panel>

          {selected.requires_human_approval&&['pending_approval','proposed'].includes(selected.status)&&
            <Panel title="HUMAN REVIEW">
              <textarea
                className="dc-review-input"
                value={reviewComment}
                onChange={e=>setReviewComment(e.target.value)}
                placeholder="Justificación obligatoria para aprobar o rechazar esta recomendación…"
                rows={4}
              />
              {reviewError&&<div className="dc-review-error">{reviewError}</div>}
              <div className="dc-review-actions">
                <button className="dc-reject" onClick={()=>review('rejected')} disabled={reviewing}>
                  <XCircle size={15}/> Rechazar
                </button>
                <button className="dc-approve" onClick={()=>review('approved')} disabled={reviewing}>
                  <CheckCircle2 size={15}/> Aprobar
                </button>
              </div>
            </Panel>
          }
        </div>
      </div>}
  </section>
}

function Panel({title,children}){
  return <div className="dc-panel"><div className="dc-panel-title">{title}</div>{children}</div>
}
