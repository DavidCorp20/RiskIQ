import { useCallback, useEffect, useRef, useState } from 'react'
import { getPortfolioEWS } from '../api'

export function usePortfolioEWS(datasetId, options = {}) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const requestId = useRef(0)
  const refresh = useCallback(async () => {
    if (!datasetId) { setData(null); setError(''); return null }
    const id = ++requestId.current
    setLoading(true); setError('')
    try { const response = await getPortfolioEWS(datasetId, options); if (id === requestId.current) setData(response); return response }
    catch (e) { if (id === requestId.current) { setData(null); setError(e?.message || 'Unable to load portfolio EWS evidence') } return null }
    finally { if (id === requestId.current) setLoading(false) }
  }, [datasetId, JSON.stringify(options)])
  useEffect(() => { refresh(); return () => { requestId.current += 1 } }, [refresh])
  return { data, loading, error, refresh }
}
