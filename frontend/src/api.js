const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

async function request(url, options = {}) {
  const response = await fetch(`${API_URL}${url}`, options)
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail?.message || data.detail || `API error ${response.status}`)
  return data
}

export const runWorkspace = payload => request('/api/v1/workspace/run', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})

export async function discoverFile(file) {
  const form = new FormData(); form.append('file', file)
  return request('/api/v1/data/discover', {method:'POST',body:form})
}

export async function ingestFile(file, mappings, datasetId = '') {
  const form = new FormData(); form.append('file', file); form.append('mappings', JSON.stringify(mappings)); if(datasetId) form.append('dataset_id', datasetId)
  return request('/api/v1/data/ingest', {method:'POST',body:form})
}

export const databaseHealth = () => request('/api/v1/data/health')
