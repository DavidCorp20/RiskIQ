import {useEffect,useMemo,useState} from 'react'
import {getAnalysisCatalog,getDatasetRecords} from './api'
import './analysis-library.css'

const groupLabels={
  core:'Core',
  scenario:'Scenarios',
  advanced_risk:'Advanced risk',
}

export default function AnalysisLibrary({datasetId=''}){
  const [catalog,setCatalog]=useState({indicators:[],models:[]})
  const [fields,setFields]=useState([])
  const [selected,setSelected]=useState('portfolio_health')
  const [loading,setLoading]=useState(false)
  const [error,setError]=useState('')

  useEffect(()=>{
    let active=true
    ;(async()=>{
      try{
        setLoading(true);setError('')
        let available=[]
        if(datasetId){
          const result=await getDatasetRecords(datasetId)
          const sample=(result?.records||[]).slice(0,50)
          const names=new Set()
          sample.forEach(row=>Object.keys(row||{}).forEach(key=>names.add(key)))
          available=[...names]
        }
        const data=await getAnalysisCatalog(available)
        if(active){setFields(available);setCatalog(data||{indicators:[],models:[]})}
      }catch(err){if(active)setError(err?.message||'No se pudo cargar la biblioteca de análisis')}finally{if(active)setLoading(false)}
    })()
    return()=>{active=false}
  },[datasetId])

  const models=useMemo(()=>catalog.models||[],[catalog])
  const indicators=useMemo(()=>catalog.indicators||[],[catalog])
  const current=models.find(item=>item.id===selected)||models[0]

  return <section className="analysis-library">
    <div className="analysis-library-head">
      <div>
        <span>ANALYSIS ENGINE</span>
        <h2>Biblioteca de análisis</h2>
        <p>Selecciona una metodología. RiskIQ verifica primero si la cartera contiene los datos necesarios.</p>
      </div>
      <div className="analysis-library-meta">
        <strong>{fields.length||'—'}</strong>
        <span>campos detectados</span>
      </div>
    </div>

    {error&&<div className="analysis-library-error">{error}</div>}
    {loading&&<div className="analysis-library-state">Analizando disponibilidad de modelos…</div>}

    {!loading&&<div className="analysis-library-grid">
      <div className="analysis-library-list">
        {models.map(model=>{
          const ready=model.readiness?.ready===true
          return <button key={model.id} className={`analysis-model ${selected===model.id?'selected':''}`} onClick={()=>setSelected(model.id)}>
            <span>
              <b>{model.name}</b>
              <small>{groupLabels[model.category]||model.category}</small>
            </span>
            <em className={ready?'ready':'planned'}>{ready?'LISTO':model.status==='planned'?'PRÓXIMAMENTE':'NO LISTO'}</em>
          </button>
        })}
      </div>

      {current&&<div className="analysis-model-detail">
        <span className="detail-kicker">MODELO SELECCIONADO</span>
        <h3>{current.name}</h3>
        <p>{current.question}</p>
        <div className="detail-section"><span>Indicadores utilizados</span><div className="tag-row">{(current.indicators||[]).map(id=><i key={id}>{id}</i>)}</div></div>
        <div className="detail-section"><span>Datos requeridos</span><div className="requirement-list">{(current.requires||[]).map(field=>{
          const present=fields.length===0||fields.includes(field)
          return <div key={field}><b>{present?'✓':'!'}</b><span>{field}</span></div>
        })}</div></div>
        <div className="detail-footer">{current.readiness?.ready?'La cartera tiene lo necesario para ejecutar este modelo.':'Este modelo requiere datos adicionales o todavía pertenece a una capacidad futura.'}</div>
      </div>}
    </div>}

    <div className="indicator-library">
      <div><span>INDICATOR LIBRARY</span><strong>Indicadores disponibles</strong></div>
      <div className="indicator-tags">{indicators.slice(0,12).map(ind=><span key={ind.id}>{ind.name}</span>)}</div>
    </div>
  </section>
}
