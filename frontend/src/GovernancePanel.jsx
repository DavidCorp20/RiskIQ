import React,{useEffect,useMemo,useState} from 'react'
import {clonePolicyVersion,listDecisionRules,listPolicyVersions,transitionPolicy} from './api'
import './governance-panel.css'

const readActive=()=>{try{return JSON.parse(localStorage.getItem('riskiq.activeDataset')||'null')?.dataset_id||''}catch{return ''}}
const NEXT={DRAFT:['TESTING'],TESTING:['DRAFT','APPROVED'],APPROVED:['DEPLOYED'],DEPLOYED:['RETIRED'],RETIRED:[]}

export default function GovernancePanel(){
 const [datasetId,setDatasetId]=useState(readActive()),[rules,setRules]=useState([]),[policyId,setPolicyId]=useState(''),[versions,setVersions]=useState([]),[selected,setSelected]=useState(null),[busy,setBusy]=useState(false),[message,setMessage]=useState('Governance control ready')
 const current=useMemo(()=>selected||versions[versions.length-1]||null,[selected,versions])
 const load=async()=>{if(!policyId)return;try{const r=await listPolicyVersions(policyId,datasetId);setVersions(r?.versions||[]);setSelected((r?.versions||[]).slice(-1)[0]||null)}catch(e){setMessage('Error · '+e.message)}}
 useEffect(()=>{listDecisionRules(datasetId).then(r=>{const x=r?.items||[];setRules(x);setPolicyId(x[0]?.id||'')}).catch(()=>setRules([]))},[datasetId])
 useEffect(()=>{load()},[policyId,datasetId])
 const act=async(status)=>{if(!current)return;setBusy(true);try{await transitionPolicy(policyId,status,current.version,datasetId,'user');setMessage(`Lifecycle · v${current.version} → ${status}`);await load()}catch(e){setMessage('Transition blocked · '+e.message)}finally{setBusy(false)}}
 const clone=async()=>{if(!current)return;setBusy(true);try{const r=await clonePolicyVersion(policyId,current.version,datasetId,'user','New controlled policy revision');setMessage(`New draft created · v${r.version}`);await load();setSelected({version:r.version,status:'DRAFT',governance:{parent_version:current.version}})}catch(e){setMessage('Clone failed · '+e.message)}finally{setBusy(false)}}
 return <section className="ri-governance-shell">
  <div className="ri-governance-head"><div><div className="ri-kicker">GOVERNANCE · POLICY LIFECYCLE</div><h2>Version control before production</h2><p>Every policy version has a controlled lifecycle. Approved and deployed versions are not edited in place; changes start from a new cloned draft.</p></div><span className="ri-chip">IMMUTABLE VERSIONS</span></div>
  <div className="ri-governance-toolbar"><label>POLICY<select value={policyId} onChange={e=>setPolicyId(e.target.value)}><option value="">Select policy…</option>{rules.map(r=><option key={r.id} value={r.id}>{r.name}</option>)}</select></label><label>DATASET<select value={datasetId} onChange={e=>setDatasetId(e.target.value)}><option value="">All datasets</option></select></label><button className="ri-gov-btn" disabled={busy||!current} onClick={clone}>Clone as new version</button></div>
  {!current?<div className="ri-governance-empty">Save a Policy Package first. Governance will then expose its version history and lifecycle controls.</div>:<>
   <div className="ri-gov-lifecycle">{['DRAFT','TESTING','APPROVED','DEPLOYED','RETIRED'].map((s,i)=><React.Fragment key={s}><div className={`ri-gov-step ${current.status===s?'is-current':''} ${versions.some(v=>v.status===s)?'is-seen':''}`}><span>{String(i+1).padStart(2,'0')}</span><b>{s}</b><small>{s==='DRAFT'?'Editable':s==='TESTING'?'Validation':s==='APPROVED'?'Controlled release':s==='DEPLOYED'?'Production':'Historical record'}</small></div>{i<4&&<i>→</i>}</React.Fragment>)}</div>
   <div className="ri-gov-grid"><div className="ri-panel"><div className="ri-panel-head"><div><div className="ri-eyebrow">Current controlled version</div><h3>v{current.version} · {current.status}</h3></div><span className="ri-pill">{current.governance?.created_by||'user'}</span></div><div className="ri-gov-meta"><div><span>Created</span><b>{current.governance?.created_at||current.saved_at||'—'}</b></div><div><span>Parent</span><b>{current.governance?.parent_version?`v${current.governance.parent_version}`:'—'}</b></div><div><span>Approved by</span><b>{current.governance?.approved_by||'—'}</b></div><div><span>Deployed by</span><b>{current.governance?.deployed_by||'—'}</b></div></div><div className="ri-gov-actions">{(NEXT[current.status]||[]).map(s=><button key={s} disabled={busy} onClick={()=>act(s)}>{busy?'Working…':`Move to ${s}`}</button>)}</div></div>
   <div className="ri-panel"><div className="ri-panel-head"><div><div className="ri-eyebrow">Version history</div><h3>Controlled revisions</h3></div></div><div className="ri-version-list">{versions.slice().reverse().map(v=><button className={current.version===v.version?'is-selected':''} key={v.version} onClick={()=>setSelected(v)}><span>v{v.version}</span><b>{v.status}</b><small>{v.governance?.parent_version?`from v${v.governance.parent_version}`:'root version'}</small></button>)}</div></div></div>
  </>}
  <div className="ri-gov-status">{message}</div>
 </section>
}
