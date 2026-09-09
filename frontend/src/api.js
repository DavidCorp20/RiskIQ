const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

export async function runWorkspace(payload) {
  const response = await fetch(`${API_URL}/api/v1/workspace/run`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || `API error ${response.status}`)
  return data
}

export async function assessFile(file) {
  const form = new FormData(); form.append('file', file)
  const response = await fetch(`${API_URL}/api/v1/data/ingest`, { method: 'POST', body: form })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || `API error ${response.status}`)
  return data
}
