import {useState} from 'react'
import {AlertTriangle,CheckCircle2,ChevronRight,Info,Loader2,Merge,ShieldCheck,X} from 'lucide-react'

const money=value=>value===null||value===undefined||value===''?'—':typeof value==='number'?value.toLocaleString():String(value)

export default function ReconciliationPanel({report,resolutions,setResolutions,reason,setReason,onCancel,onCommit,onBulkOverride,loading,bulkLoading}){
 const conflicts=(report?.items||[]).filter(item=>item.classification==='conflict')
 const unresolved=conflicts.filter(item=>!resolutions[item.key])
 const [expanded,setExpanded]=useState(conflicts[0]?.key||'')
 const [bulkOpen,setBulkOpen]=useState(false)
 const [bulkReason,setBulkReason]=useState(reason||'')
 const counts=report?.counts||{}

 async function confirmBulk(){
  if(!bulkReason.trim()) return
  await onBulkOverride(bulkReason.trim())
  setBulkOpen(false)
 }

 return (
  <div className="fixed inset-0 z-[80] flex items-start justify-center overflow-auto bg-slate-950/40 p-4 pt-16" role="dialog" aria-modal="true" aria-label="Reconciliación histórica">
   <div className="w-full max-w-5xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
    <header className="flex items-start justify-between border-b border-slate-200 px-6 py-5">
     <div>
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500"><Merge size={14}/> Historical reconciliation</div>
      <h2 className="mt-1 text-xl font-semibold text-slate-950">Revisión de carga antes de actualizar el histórico</h2>
      <p className="mt-1 max-w-3xl text-sm text-slate-500">RiskIQ detectó observaciones existentes. No crea duplicados ni cambia silenciosamente un snapshot financiero.</p>
     </div>
     <button type="button" onClick={onCancel} className="rounded-md p-2 text-slate-400 hover:bg-slate-100" aria-label="Cerrar"><X size={18}/></button>
    </header>

    <div className="grid grid-cols-2 gap-3 border-b border-slate-200 bg-slate-50 p-5 sm:grid-cols-4">
     {Object.entries({inserted:'Nuevas',identical:'Idénticas',enriched:'Enriquecidas',conflict:'Conflictos'}).map(([type,text])=>(
      <div key={type} className="rounded-xl border border-slate-200 bg-white px-4 py-3">
       <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{text}</div>
       <div className="mt-1 text-2xl font-semibold text-slate-950">{counts[type]||0}</div>
       <div className="mt-1 text-xs text-slate-500">{type==='inserted'?'se incorporan':type==='identical'?'se omiten':type==='enriched'?'se fusionan':'requieren decisión'}</div>
      </div>
     ))}
    </div>

    <main className="space-y-5 p-6">
     {(counts.identical||0)>0 && <div className="flex gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3"><CheckCircle2 size={18} className="mt-0.5 text-slate-600"/><div><div className="text-sm font-semibold text-slate-800">Observaciones idénticas</div><div className="text-sm text-slate-600">Las copias exactas se omiten y quedan registradas en Audit Ledger.</div></div></div>}
     {(counts.enriched||0)>0 && <div className="flex gap-3 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3"><Merge size={18} className="mt-0.5 text-blue-700"/><div><div className="text-sm font-semibold text-blue-900">Observaciones enriquecidas</div><div className="text-sm text-blue-800">Solo se completan atributos que estaban vacíos; los valores poblados no se reemplazan.</div></div></div>}

     {conflicts.length>0 && <section className="rounded-xl border border-amber-200 bg-amber-50/60">
      <div className="flex flex-col gap-3 border-b border-amber-200 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
       <div className="flex gap-3"><AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-700"/><div><div className="text-sm font-semibold text-amber-950">Conflictos financieros</div><div className="text-sm text-amber-900">{conflicts.length.toLocaleString()} observaciones tienen cambios materiales.</div></div></div>
       <button type="button" disabled={bulkLoading} onClick={()=>{setBulkReason(reason||'');setBulkOpen(true)}} className="inline-flex shrink-0 items-center justify-center gap-2 rounded-md border border-amber-400 bg-white px-3 py-2 text-xs font-semibold text-amber-900 hover:bg-amber-50 disabled:opacity-50"><ShieldCheck size={14}/>{bulkLoading?'Aplicando…':'Forzar Todos los Conflictos'}</button>
      </div>

      <div className="divide-y divide-amber-200">
       {conflicts.map(item=>(
        <div key={item.key} className="bg-white/70 px-4 py-3">
         <button type="button" onClick={()=>setExpanded(expanded===item.key?'':item.key)} className="flex w-full items-center justify-between text-left">
          <div><div className="text-sm font-semibold text-slate-900">{item.loan_id} · {item.snapshot_date}</div><div className="text-xs text-slate-500">{item.conflicts?.length||0} campo(s) diferente(s){resolutions[item.key]&&<span className="ml-2 font-semibold uppercase">· {resolutions[item.key]==='force'?'FORZAR':'MANTENER'}</span>}</div></div>
          <ChevronRight size={16} className={`text-slate-400 transition ${expanded===item.key?'rotate-90':''}`}/>
         </button>
         {expanded===item.key && <div className="mt-3 space-y-2">
          {(item.conflicts||[]).map(change=>(
           <div key={change.field} className="grid grid-cols-[1fr_1fr_1fr] gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs">
            <div><div className="font-semibold text-slate-700">{change.field}</div>{change.critical&&<span className="text-[10px] font-semibold uppercase text-amber-700">financiero crítico</span>}</div>
            <div><div className="uppercase tracking-wide text-slate-400">Histórico</div><div className="font-medium text-slate-800">{money(change.previous)}</div></div>
            <div><div className="uppercase tracking-wide text-slate-400">Nuevo</div><div className="font-medium text-slate-800">{money(change.incoming)}</div></div>
           </div>
          ))}
          <div className="flex flex-wrap gap-2 pt-1">
           <button type="button" onClick={()=>setResolutions(prev=>({...prev,[item.key]:'keep'}))} className={`rounded-md border px-3 py-2 text-xs font-semibold ${resolutions[item.key]==='keep'?'border-slate-800 bg-slate-900 text-white':'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'}`}>Mantener histórico original</button>
           <button type="button" onClick={()=>setResolutions(prev=>({...prev,[item.key]:'force'}))} className={`rounded-md border px-3 py-2 text-xs font-semibold ${resolutions[item.key]==='force'?'border-amber-700 bg-amber-700 text-white':'border-amber-300 bg-white text-amber-800 hover:bg-amber-50'}`}>Forzar actualización</button>
          </div>
         </div>}
        </div>
       ))}
      </div>
     </section>}

     {Object.values(resolutions).some(value=>value==='force') && <div className="rounded-xl border border-slate-200 bg-white p-4"><label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Justificación de actualización</label><textarea value={reason} onChange={event=>setReason(event.target.value)} rows={2} placeholder="Ej.: corrección de saldo reportado por la fuente oficial del cierre." className="mt-2 w-full rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-800 outline-none focus:border-slate-400"/><div className="mt-2 flex gap-2 text-xs text-slate-500"><ShieldCheck size={14}/> La decisión y los valores anterior/nuevo quedan registrados en Audit Ledger.</div></div>}
     <div className="flex items-start gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3"><Info size={16} className="mt-0.5 text-slate-500"/><div className="text-xs leading-5 text-slate-600">La identidad histórica sigue siendo <strong>loan_id + snapshot_date</strong>. La proyección point-in-time se reconstruye al confirmar.</div></div>

     <footer className="flex flex-col-reverse gap-2 border-t border-slate-200 pt-4 sm:flex-row sm:justify-end">
      <button type="button" onClick={onCancel} className="h-10 rounded-md border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700">Cancelar carga</button>
      <button type="button" disabled={loading||unresolved.length>0} onClick={onCommit} className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-slate-900 px-4 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-40">{loading?<Loader2 size={15} className="animate-spin"/>:<CheckCircle2 size={15}/>} {unresolved.length?`Resolver ${unresolved.length} conflicto(s)`:'Aplicar reconciliación y analizar'}</button>
     </footer>
    </main>
   </div>

   {bulkOpen && <div className="fixed inset-0 z-[95] flex items-center justify-center bg-slate-950/55 p-4" role="presentation">
    <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl" role="alertdialog" aria-modal="true" aria-labelledby="bulk-override-title">
     <div className="flex items-start gap-3"><div className="rounded-full bg-amber-100 p-2 text-amber-700"><AlertTriangle size={20}/></div><div><h3 id="bulk-override-title" className="text-lg font-semibold text-slate-950">Confirmar actualización masiva</h3><p className="mt-1 text-sm leading-5 text-slate-600">Se sobrescribirán campos financieros críticos en <strong>{conflicts.length.toLocaleString()} observaciones históricas</strong>, como saldo, DPD, estado, pagos o cuotas. Esta acción modifica el histórico point-in-time y será auditada.</p></div></div>
     <div className="mt-5"><label className="text-xs font-semibold uppercase tracking-wider text-slate-600">Justificación de auditoría <span className="text-amber-700">*</span></label><textarea autoFocus value={bulkReason} onChange={event=>setBulkReason(event.target.value)} rows={4} placeholder="Explica por qué la fuente oficial requiere esta actualización masiva…" className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-800 outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500"/><p className="mt-1 text-xs text-slate-500">La misma justificación se asociará a cada evento del Audit Ledger.</p></div>
     <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end"><button type="button" onClick={()=>setBulkOpen(false)} className="h-10 rounded-md border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700">Cancelar</button><button type="button" disabled={!bulkReason.trim()||bulkLoading} onClick={confirmBulk} className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-amber-700 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-800 disabled:opacity-40">{bulkLoading?<Loader2 size={15} className="animate-spin"/>:<ShieldCheck size={15}/>} Confirmar y forzar {conflicts.length.toLocaleString()} conflictos</button></div>
    </div>
   </div>}
  </div>
 )
}
