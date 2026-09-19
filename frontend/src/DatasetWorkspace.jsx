import {useEffect,useState} from 'react'
import {getDataset,listDatasets,runDataset} from './api'
import DecisionCenter from './DecisionCenter'

export default function DatasetWorkspace({activeDataset,onSelect,onResult}){
  const [datasets,setDatasets]=useState([])
  const [loading,setLoading]=useState(false)
  const [running,setRunning]=useState(false)
  const [error,setError]=useState('')
  const [decisionEngine,setDecisionEngine]=useState(null)

  async function load(){
    setLoading(true);setError('')
    try{
      const r=await listDatasets()
      const items=r.datasets||[]
      setDatasets(items)
      if(!activeDataset?.dataset_id && items[0]?.dataset_id) onSelect(items[0])
    }catch(e){setError(e.message)}finally{setLoading(false)}
  }
  useEffect(()=>{load()},[])

  async function select(id){
    setLoading(true);setError('');setDecisionEngine(null)
    try{
      const r=await getDataset(id)
      onSelect(r)
      const intelligence=await runDataset(id)
      setDecisionEngine(intelligence.decision_engine||null)
      onResult(intelligence)
    }catch(e){setError(e.message)}finally{setLoading(false)}
  }

  async function run(){
    if(!activeDataset?.dataset_id)return
    setRunning(true);setError('')
    try{
      const r=await runDataset(activeDataset.dataset_id)
      setDecisionEngine(r.decision_engine||null)
      onResult(r)
    }catch(e){setError(e.message)}finally{setRunning(false)}
  }

  return <section className="content">
    <Card>
      <SectionTitle title="Dataset Workspace"/>
      <p className="muted">Fuente única de verdad: selecciona un dataset persistido y ejecuta el mismo contrato de inteligencia que alimenta Portfolio, Risk Analytics y Decision Center.</p>
      <div className="button-row"><button className="primary" onClick={load}>{loading?'Loading…':'Refresh datasets'}</button>{activeDataset?.dataset_id&&<button className="primary" onClick={run}>{running?'Running…':'Run selected dataset'}</button>}</div>
      {error&&<div className="error">{error}</div>}
    </Card>
    <Card>
      <SectionTitle title="Persisted datasets"/>
      {datasets.length===0?<div className="empty">No persisted datasets yet. Upload a CSV/XLSX from Data to create the first portfolio.</div>:
      <div className="cards-list">{datasets.map(d=><button className={`decision dataset-row ${activeDataset?.dataset_id===d.dataset_id?'selected':''}`} key={d.dataset_id} onClick={()=>select(d.dataset_id)}>
        <div><Badge tone={d.quality_status==='pass'||d.quality?.status==='pass'?'ok':'neutral'}>{d.quality_status||d.quality?.status||'persisted'}</Badge><h3>{d.source_name||d.dataset_id}</h3><p>{d.dataset_id} · {d.row_count??d.source_rows??'—'} source rows · created {d.created_at||'—'}</p></div><span>{activeDataset?.dataset_id===d.dataset_id?'ACTIVE':'Select'}</span>
      </button>)}</div>}
    </Card>
    {activeDataset?.dataset_id&&<Card><SectionTitle title="Active dataset"/><div className="grid four"><Metric title="Dataset ID" value={activeDataset.dataset_id}/><Metric title="Source" value={activeDataset.source_name||activeDataset.metadata?.source_name||'—'}/><Metric title="Rows" value={activeDataset.row_count??activeDataset.metadata?.source_rows??'—'}/><Metric title="Quality" value={activeDataset.quality_score??activeDataset.metadata?.quality?.quality_score??activeDataset.quality_status??'—'}/></div><p className="muted">All subsequent analysis is bound to this dataset_id. No demo portfolio is used when a persisted dataset is active.</p></Card>}
    {activeDataset?.dataset_id&&<DecisionCenter decisionEngine={decisionEngine}/>} 
  </section>
}

const Card=({children,className=''})=><div className={`card ${className}`}>{children}</div>
const Badge=({children,tone='neutral'})=><span className={`badge ${tone}`}>{children}</span>
const Metric=({title,value})=><Card className="metric"><span>{title}</span><strong>{value}</strong><small>Dataset registry</small></Card>
const SectionTitle=({title})=><div className="section-title"><h3>{title}</h3></div>
