import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, FileJson, ShieldCheck } from 'lucide-react'
import { getPortfolioDashboard, listAuditDecisions } from './api'
import PortfolioToolbar from './PortfolioToolbar'
import PortfolioKpiGrid from './PortfolioKpiGrid'
import RatingDistribution from './RatingDistribution'
import ExposureHeatmap from './ExposureHeatmap'
import VintageMatrix from './VintageMatrix'
import './portfolio-dashboard.css'

export default function PortfolioDashboard({datasetId}){
 const [data,setData]=useState(null),[segment,setSegment]=useState(''),[cutoffDate,setCutoffDate]=useState(''),[loading,setLoading]=useState(true),[error,setError]=useState(''),[audit,setAudit]=useState([])
 const load=useCallback(async()=>{if(!datasetId)return;setLoading(true);setError('');try{const d=await getPortfolioDashboard(datasetId,{segment,cutoffDate});setData(d);const a=await listAuditDecisions(datasetId);setAudit(a?.items||[])}catch(e){setError(e.message||'No se pudo cargar Portfolio')}finally{setLoading(false)}},[datasetId,segment,cutoffDate])
 useEffect(()=>{load()},[load])
 function exportJson(){const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='riskiq-portfolio-'+datasetId+'.json';a.click();URL.revokeObjectURL(url)}
 if(loading&&!data)return <div className="portfolio-loading"><div className="portfolio-skeleton portfolio-skeleton-wide"/><div className="portfolio-skeleton"/><div className="portfolio-skeleton"/></div>
 if(error)return <div className="portfolio-error"><AlertTriangle size={17}/><span>{error}</span><button onClick={load}>Reintentar</button></div>
 if(!data)return <div className="portfolio-empty-state"><ShieldCheck size={22}/><h2>Portfolio sin datos</h2><p>Selecciona una cartera para construir el reporte ejecutivo.</p></div>
 return <div className="portfolio-dashboard">
  <PortfolioToolbar data={data} segment={segment} cutoffDate={cutoffDate} onSegmentChange={setSegment} onCutoffChange={setCutoffDate} onRefresh={load} onExport={exportJson} loading={loading}/>
  <PortfolioKpiGrid kpis={data.kpis}/>
  <div className="portfolio-dashboard-grid"><RatingDistribution data={data.rating_distribution}/><ExposureHeatmap data={data.heatmap}/></div>
  <VintageMatrix data={data.vintage}/>
  <section className="portfolio-panel"><div className="portfolio-panel-heading"><div><span>RISK INSIGHTS</span><h3>Insights de Risk</h3></div><small>{data.insights?.length||0} observaciones determinísticas</small></div><div className="portfolio-insights">{(data.insights||[]).map((x,i)=><article className="portfolio-insight" key={x.type||i}><b>{x.title}</b><p>{x.message}</p></article>)}</div></section>
  <section className="portfolio-panel"><div className="portfolio-panel-heading"><div><span>AUDIT</span><h3>Audit trail</h3></div><small><FileJson size={13}/> {audit.length} registros</small></div>{audit.length?<div className="portfolio-audit-list">{audit.slice(0,8).map((x,i)=><div key={x.decision_id||i}><b>{x.title||x.decision_code}</b><span>{x.status||'proposed'} · {x.actor||'system'} · {x.created_at||'—'}</span></div>)}</div>:<div className="portfolio-empty">No hay decisiones auditadas para esta cartera.</div>}</section>
 </div>
}
