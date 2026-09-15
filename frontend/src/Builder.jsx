import {useEffect,useMemo,useState} from 'react'
import DataFoundation from './DataFoundation'
import DiagnosisBrief from './DiagnosisBrief'
import IndicatorStudio from './IndicatorStudio'
import DecisionStudio from './DecisionStudio'
import AnalysisLibrary from './AnalysisLibrary'
import PolicyPortfolioLab from './PolicyPortfolioLab'
import PolicyBacktest from './PolicyBacktest'
import GovernancePanel from './GovernancePanel'

const stages=[
  {id:'data',label:'Data Foundation',short:'Datos',description:'Descubre, mapea y valida la evidencia de cartera.'},
  {id:'diagnosis',label:'Diagnosis',short:'Diagnóstico',description:'Convierte evidencia en hallazgos priorizados.'},
  {id:'indicators',label:'Indicator Studio',short:'Indicadores',description:'Construye y evalúa indicadores de riesgo.'},
  {id:'analysis',label:'Analysis Library',short:'Modelos',description:'Consulta modelos y análisis reutilizables.'},
  {id:'decisions',label:'Decision Studio',short:'Decisiones',description:'Diseña decisiones sobre hechos calculados.'},
  {id:'policies',label:'Policy Lab',short:'Políticas',description:'Prueba políticas antes de activarlas.'},
  {id:'backtest',label:'Policy Backtest',short:'Backtest',description:'Reproduce decisiones sobre evidencia histórica.'},
  {id:'governance',label:'Governance',short:'Gobierno',description:'Mantén trazabilidad, control y revisión humana.'}
]

export default function Builder({datasetId=''}){
  const [activeDataset,setActiveDataset]=useState(datasetId)
  const [stage,setStage]=useState('data')
  useEffect(()=>{
    if(datasetId){setActiveDataset(datasetId);return}
    try{setActiveDataset(JSON.parse(localStorage.getItem('riskiq.activeDataset')||'null')?.dataset_id||'')}catch{setActiveDataset('')}
  },[datasetId])

  const current=useMemo(()=>stages.find(x=>x.id===stage)||stages[0],[stage])
  const index=stages.findIndex(x=>x.id===current.id)
  const go=direction=>{
    const next=Math.min(stages.length-1,Math.max(0,index+direction))
    setStage(stages[next].id)
  }
  const datasetLabel=activeDataset||'Sin cartera seleccionada'

  return <div className="riskiq-decision-workspace builder-shell">
    <div className="builder-context">
      <div><span>PORTFOLIO CONTEXT</span><strong>{datasetLabel}</strong></div>
      <div className="builder-context-status"><i/>{activeDataset?'Evidencia vinculada':'Selecciona una cartera para comenzar'}</div>
    </div>

    <div className="builder-stage-head">
      <div>
        <span className="builder-eyebrow">RISK DECISION WORKFLOW</span>
        <h3>{current.label}</h3>
        <p>{current.description}</p>
      </div>
      <div className="builder-progress">
        <strong>{String(index+1).padStart(2,'0')}</strong><span>/ {String(stages.length).padStart(2,'0')}</span>
      </div>
    </div>

    <div className="builder-stage-nav" role="tablist" aria-label="Risk decision workflow">
      {stages.map((item,i)=><button key={item.id} type="button" role="tab" aria-selected={stage===item.id} className={stage===item.id?'active':''} onClick={()=>setStage(item.id)}>
        <span>{String(i+1).padStart(2,'0')}</span><b>{item.short}</b>
      </button>)}
    </div>

    <div className="builder-stage-body">
      {stage==='data'&&<DataFoundation datasetId={activeDataset} onContinue={()=>setStage('diagnosis')}/>} 
      {stage==='diagnosis'&&<DiagnosisBrief datasetId={activeDataset} onContinue={()=>setStage('indicators')}/>} 
      {stage==='indicators'&&<IndicatorStudio datasetId={activeDataset} onContinue={()=>setStage('analysis')}/>} 
      {stage==='analysis'&&<AnalysisLibrary datasetId={activeDataset}/>} 
      {stage==='decisions'&&<DecisionStudio datasetId={activeDataset}/>} 
      {stage==='policies'&&<PolicyPortfolioLab/>} 
      {stage==='backtest'&&<PolicyBacktest/>} 
      {stage==='governance'&&<GovernancePanel/>}
    </div>

    <div className="builder-stage-footer">
      <span>Human review required before policy activation.</span>
      <div>
        <button type="button" className="builder-nav-button secondary" onClick={()=>go(-1)} disabled={index===0}>Anterior</button>
        <button type="button" className="builder-nav-button" onClick={()=>go(1)} disabled={index===stages.length-1}>{index===stages.length-1?'Completado':'Siguiente'}</button>
      </div>
    </div>
  </div>
}