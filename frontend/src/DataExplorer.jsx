import {useEffect,useMemo,useState} from 'react'
import {BarChart3,Database,Filter,Layers3,RefreshCw,Search,SlidersHorizontal,Table2,X} from 'lucide-react'
import {getDatasetRecords} from './api'

const money=v=>`$${Number(v||0).toLocaleString(undefined,{maximumFractionDigits:0})}`
const pct=v=>`${(Number(v||0)*100).toFixed(1)}%`
const labelize=k=>String(k||'').replace(/_/g,' ').replace(/\b\w/g,m=>m.toUpperCase())
const isNumberValue=v=>v!==null&&v!==''&&!Number.isNaN(Number(v))

function metric(rows){
 const balanceKey=['outstanding_principal','outstanding_balance','balance','principal'].find(k=>rows.some(r=>isNumberValue(r?.[k])))
 const dpdKey=['dpd','days_past_due'].find(k=>rows.some(r=>isNumberValue(r?.[k])))
 const exposure=rows.reduce((a,r)=>a+Number(r?.[balanceKey]||0),0)
 const bad30=rows.reduce((a,r)=>a+(Number(r?.[dpdKey]||0)>=30?Number(r?.[balanceKey]||0):0),0)
 const bad90=rows.reduce((a,r)=>a+(Number(r?.[dpdKey]||0)>=90?Number(r?.[balanceKey]||0):0),0)
 return {exposure,par30:exposure?bad30/exposure:0,par90:exposure?bad90/exposure:0,balanceKey,dpdKey}
}

function applyCondition(row,c){
 if(!c.field)return true
 const a=row[c.field], b=c.value
 if(c.operator==='is_empty')return a===null||a===undefined||String(a).trim()===''
 if(c.operator==='is_not_empty')return a!==null&&a!==undefined&&String(a).trim()!==''
 if(c.operator==='contains')return String(a??'').toLowerCase().includes(String(b??'').toLowerCase())
 const numeric=isNumberValue(a)&&isNumberValue(b), av=numeric?Number(a):String(a??''), bv=numeric?Number(b):String(b??'')
 if(c.operator==='=')return av===bv
 if(c.operator==='!=')return av!==bv
 if(c.operator==='>')return av>bv
 if(c.operator==='>=')return av>=bv
 if(c.operator==='<')return av<bv
 if(c.operator==='<=')return av<=bv
 return true
}

export default function DataExplorer({datasetId}){
 const [rows,setRows]=useState([]),[loading,setLoading]=useState(false),[error,setError]=useState(''),[query,setQuery]=useState(''),[selectedField,setSelectedField]=useState(''),[page,setPage]=useState(1),[conditions,setConditions]=useState([]),[segmentName,setSegmentName]=useState(''),[segments,setSegments]=useState([]),[activeTab,setActiveTab]=useState('data')
 const pageSize=25
 useEffect(()=>{try{const saved=JSON.parse(localStorage.getItem(`riskiq.segments.${datasetId}`)||'[]');setSegments(Array.isArray(saved)?saved:[])}catch{setSegments([])}},[datasetId])
 const load=async()=>{if(!datasetId)return;setLoading(true);setError('');try{const r=await getDatasetRecords(datasetId);setRows(r.records||[]);setPage(1)}catch(e){setError(e.message||'No se pudieron leer los registros.')}finally{setLoading(false)}}
 useEffect(()=>{load()},[datasetId])
 const columns=useMemo(()=>{const s=new Set();rows.forEach(r=>Object.keys(r||{}).forEach(k=>s.add(k)));return [...s].filter(k=>!['_id','dataset_id'].includes(k))},[rows])
 const numericColumns=useMemo(()=>columns.filter(c=>rows.some(r=>isNumberValue(r?.[c]))),[columns,rows])
 const categoricalColumns=useMemo(()=>columns.filter(c=>!numericColumns.includes(c)),[columns,numericColumns])
 const filtered=useMemo(()=>{const q=query.trim().toLowerCase();return rows.filter(r=>{const qok=!q||columns.some(c=>String(r?.[c]??'').toLowerCase().includes(q));const cok=conditions.every(c=>applyCondition(r,c));return qok&&cok})},[rows,query,columns,conditions])
 const pageRows=filtered.slice((page-1)*pageSize,page*pageSize)
 const totalPages=Math.max(1,Math.ceil(filtered.length/pageSize))
 const summary=useMemo(()=>metric(filtered),[filtered])
 const snapshots=useMemo(()=>{const s=new Set();rows.forEach(r=>{const d=r?.snapshot_date||r?.snapshot_month||r?.as_of_date;if(d)s.add(String(d).slice(0,10))});return [...s].sort()},[rows])
 const addCondition=()=>setConditions(c=>[...c,{field:columns[0]||'',operator:'=',value:''}])
 const saveSegment=()=>{const name=segmentName.trim();if(!name||!conditions.length)return;const next=[...segments.filter(s=>s.name!==name),{name,conditions}];setSegments(next);localStorage.setItem(`riskiq.segments.${datasetId}`,JSON.stringify(next));setSegmentName('')}
 const useSegment=s=>{setConditions(s.conditions);setActiveTab('data');setPage(1)}
 const removeSegment=name=>{const next=segments.filter(s=>s.name!==name);setSegments(next);localStorage.setItem(`riskiq.segments.${datasetId}`,JSON.stringify(next))}
 return <section className="space-y-5">
  <div className="flex flex-col gap-4 rounded-lg border border-slate-200 bg-white p-5 lg:flex-row lg:items-end lg:justify-between">
   <div><div className="mb-1 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-slate-500"><Database size={14}/> DATA EXPLORER</div><h2 className="text-xl font-semibold tracking-tight text-slate-900">Datos reales de la cartera</h2><p className="mt-1 max-w-3xl text-sm text-slate-500">RiskIQ conserva las columnas del archivo original para que puedas inspeccionar exactamente qué datos alimentan el análisis.</p></div>
   <button onClick={load} disabled={loading} className="inline-flex h-9 items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"><RefreshCw size={15} className={loading?'animate-spin':''}/> Actualizar</button>
  </div>
  {error&&<div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
   {[["Filas",filtered.length],["Columnas",columns.length],["Snapshots",snapshots.length],["Exposición",money(summary.exposure)],["PAR30",pct(summary.par30)]].map(([a,b])=><div key={a} className="rounded-lg border border-slate-200 bg-white p-4"><div className="text-xs font-medium uppercase tracking-wider text-slate-500">{a}</div><div className="mt-1 text-xl font-semibold tabular-nums text-slate-900">{b}</div></div>)}
  </div>
  <div className="flex flex-wrap gap-1 border-b border-slate-200"><button onClick={()=>setActiveTab('data')} className={`inline-flex items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium ${activeTab==='data'?'border-slate-900 text-slate-900':'border-transparent text-slate-500'}`}><Table2 size={15}/> Datos</button><button onClick={()=>setActiveTab('segments')} className={`inline-flex items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium ${activeTab==='segments'?'border-slate-900 text-slate-900':'border-transparent text-slate-500'}`}><Layers3 size={15}/> Segmentos</button><button onClick={()=>setActiveTab('schema')} className={`inline-flex items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium ${activeTab==='schema'?'border-slate-900 text-slate-900':'border-transparent text-slate-500'}`}><SlidersHorizontal size={15}/> Columnas</button></div>
  {activeTab==='data'&&<>
   <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 lg:flex-row"><div className="relative min-w-0 flex-1"><Search size={15} className="absolute left-3 top-2.5 text-slate-400"/><input value={query} onChange={e=>{setQuery(e.target.value);setPage(1)}} placeholder="Buscar en todas las columnas…" className="h-9 w-full rounded-md border border-slate-200 pl-9 pr-3 text-sm outline-none focus:border-slate-400"/></div><button onClick={()=>setConditions([])} disabled={!conditions.length} className="inline-flex h-9 items-center gap-2 rounded-md border border-slate-200 px-3 text-sm text-slate-600 disabled:opacity-40"><Filter size={15}/> Limpiar filtros</button></div>
   {conditions.length>0&&<div className="rounded-lg border border-blue-200 bg-blue-50/50 p-4"><div className="mb-3 flex items-center justify-between"><div className="text-sm font-semibold text-slate-800">Filtro analítico</div><span className="text-xs text-slate-500">{filtered.length.toLocaleString()} filas</span></div><div className="space-y-2">{conditions.map((c,i)=><div key={i} className="grid gap-2 md:grid-cols-[1.2fr_1fr_1.2fr_auto]"><select value={c.field} onChange={e=>setConditions(cs=>cs.map((x,j)=>j===i?{...x,field:e.target.value}:x))} className="h-9 rounded-md border border-slate-200 bg-white px-2 text-sm">{columns.map(col=><option key={col}>{col}</option>)}</select><select value={c.operator} onChange={e=>setConditions(cs=>cs.map((x,j)=>j===i?{...x,operator:e.target.value}:x))} className="h-9 rounded-md border border-slate-200 bg-white px-2 text-sm"><option>=</option><option>!=</option><option>&gt;</option><option>&gt;=</option><option>&lt;</option><option>&lt;=</option><option>contains</option><option>is_empty</option><option>is_not_empty</option></select><input value={c.value} disabled={c.operator.includes('empty')} onChange={e=>setConditions(cs=>cs.map((x,j)=>j===i?{...x,value:e.target.value}:x))} className="h-9 rounded-md border border-slate-200 bg-white px-2 text-sm" placeholder="Valor"/><button onClick={()=>setConditions(cs=>cs.filter((_,j)=>j!==i))} className="h-9 rounded-md p-2 text-slate-400 hover:bg-white hover:text-slate-700"><X size={16}/></button></div>)}</div><div className="mt-3 flex flex-wrap gap-2"><button onClick={addCondition} className="h-8 rounded-md border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700">+ Condición</button><input value={segmentName} onChange={e=>setSegmentName(e.target.value)} placeholder="Nombre del segmento" className="h-8 rounded-md border border-slate-200 bg-white px-3 text-xs"/><button onClick={saveSegment} disabled={!segmentName.trim()} className="h-8 rounded-md bg-slate-900 px-3 text-xs font-medium text-white disabled:opacity-40">Guardar segmento</button></div></div>}
   <div className="overflow-hidden rounded-lg border border-slate-200 bg-white"><div className="overflow-auto"><table className="min-w-full border-collapse text-sm"><thead><tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-medium uppercase tracking-wider text-slate-500">{columns.map(c=><th key={c} className="whitespace-nowrap px-3 py-2.5">{c}</th>)}</tr></thead><tbody>{pageRows.map((r,i)=><tr key={r._id||i} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">{columns.map(c=><td key={c} className="max-w-[240px] whitespace-nowrap px-3 py-2 text-slate-700">{String(r?.[c]??'—')}</td>)}</tr>)}</tbody></table>{!pageRows.length&&<div className="p-10 text-center text-sm text-slate-500">No hay filas que coincidan con el filtro.</div>}</div><div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 text-xs text-slate-500"><span>{filtered.length.toLocaleString()} filas · página {page} de {totalPages}</span><div className="flex gap-2"><button disabled={page<=1} onClick={()=>setPage(p=>p-1)} className="rounded border border-slate-200 px-2 py-1 disabled:opacity-40">Anterior</button><button disabled={page>=totalPages} onClick={()=>setPage(p=>p+1)} className="rounded border border-slate-200 px-2 py-1 disabled:opacity-40">Siguiente</button></div></div></div>
  </>}
  {activeTab==='segments'&&<div className="grid gap-4 lg:grid-cols-2"><div className="rounded-lg border border-slate-200 bg-white p-5"><div className="mb-3 flex items-center gap-2"><Layers3 size={17}/><h3 className="font-semibold text-slate-900">Segmentos guardados</h3></div>{segments.length?segments.map(s=><div key={s.name} className="flex items-center justify-between border-b border-slate-100 py-3 last:border-0"><div><div className="text-sm font-medium text-slate-800">{s.name}</div><div className="text-xs text-slate-500">{s.conditions.length} condición(es)</div></div><div className="flex gap-2"><button onClick={()=>useSegment(s)} className="rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-medium">Analizar</button><button onClick={()=>removeSegment(s.name)} className="p-1.5 text-slate-400 hover:text-red-600"><X size={15}/></button></div></div>):<p className="text-sm text-slate-500">Todavía no hay segmentos guardados.</p>}</div><div className="rounded-lg border border-slate-200 bg-white p-5"><div className="mb-3 flex items-center gap-2"><BarChart3 size={17}/><h3 className="font-semibold text-slate-900">Resultado del filtro actual</h3></div><div className="grid grid-cols-2 gap-3"><div><span className="text-xs text-slate-500">Filas</span><strong className="block text-xl">{filtered.length.toLocaleString()}</strong></div><div><span className="text-xs text-slate-500">Exposición</span><strong className="block text-xl">{money(summary.exposure)}</strong></div><div><span className="text-xs text-slate-500">PAR30</span><strong className="block text-xl">{pct(summary.par30)}</strong></div><div><span className="text-xs text-slate-500">PAR90</span><strong className="block text-xl">{pct(summary.par90)}</strong></div></div><p className="mt-4 text-xs text-slate-500">El segmento es una vista analítica sobre los datos originales; no modifica la cartera.</p></div></div>}
  {activeTab==='schema'&&<div className="overflow-hidden rounded-lg border border-slate-200 bg-white"><table className="min-w-full text-sm"><thead className="bg-slate-50 text-left text-xs uppercase tracking-wider text-slate-500"><tr><th className="px-4 py-3">Columna</th><th className="px-4 py-3">Tipo observado</th><th className="px-4 py-3">Valores no vacíos</th><th className="px-4 py-3">Ejemplos</th></tr></thead><tbody>{columns.map(c=>{const vals=rows.map(r=>r?.[c]).filter(v=>v!==null&&v!==undefined&&String(v)!=='');const type=vals.length&&vals.every(isNumberValue)?'numérico':'texto/fecha';return <tr key={c} className="border-t border-slate-100"><td className="px-4 py-3 font-medium text-slate-800">{c}</td><td className="px-4 py-3 text-slate-600">{type}</td><td className="px-4 py-3 tabular-nums text-slate-600">{vals.length.toLocaleString()} / {rows.length.toLocaleString()}</td><td className="max-w-[480px] px-4 py-3 text-slate-500">{[...new Set(vals.map(v=>String(v)))].slice(0,5).join(' · ')}</td></tr>})}</tbody></table></div>}
 </section>
}
