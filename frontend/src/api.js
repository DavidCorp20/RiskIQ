const API_URL=(import.meta.env.VITE_API_URL||'http://localhost:8000').replace(/\/$/,'')
async function request(url,options={}){const response=await fetch(`${API_URL}${url}`,options);const data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(data.detail?.message||data.detail||`API error ${response.status}`);return data}
export const runWorkspace=p=>request('/api/v1/workspace/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)})
export async function discoverFile(file){const f=new FormData();f.append('file',file);return request('/api/v1/data/discover',{method:'POST',body:f})}
export async function ingestFile(file,mappings,datasetId=''){const f=new FormData();f.append('file',file);f.append('mappings',JSON.stringify(mappings));if(datasetId)f.append('dataset_id',datasetId);return request('/api/v1/data/ingest',{method:'POST',body:f})}
export const databaseHealth=()=>request('/api/v1/data/health')
export const getDatasetPortfolio=id=>request(`/api/v1/datasets/${encodeURIComponent(id)}/portfolio`)
export const getDatasetRecords=id=>request(`/api/v1/datasets/${encodeURIComponent(id)}/records`)
export const analyzePortfolio=rows=>request('/api/v1/portfolio/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(rows)})
export const buildSnapshot=p=>request('/api/v1/portfolio/snapshot',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)})
export const runDataset=(id,payload={})=>request(`/api/v1/datasets/${encodeURIComponent(id)}/run`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
export const runSimulator=payload=>request('/api/v1/simulator/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
export const runNPL=rows=>request('/api/v1/risk/npl',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(rows)})
export const askCopilot=payload=>request('/api/v1/ai/copilot',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
