import { useCallback, useEffect, useRef, useState } from 'react'
import { getPortfolioDashboard } from '../api'

export function usePortfolioDashboard(datasetId, options = {}) {
  const { segment = '', cutoffDate = '' } = options
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(Boolean(datasetId))
  const [error, setError] = useState('')
  const requestRef = useRef(0)

  const refresh = useCallback(async () => {
    if (!datasetId) {
      setData(null)
      setLoading(false)
      setError('')
      return null
    }

    const requestId = ++requestRef.current
    setLoading(true)
    setError('')

    try {
      const result = await getPortfolioDashboard(datasetId, { segment, cutoffDate })
      if (requestId !== requestRef.current) return null
      setData(result)
      return result
    } catch (err) {
      if (requestId !== requestRef.current) return null
      setData(null)
      setError(err?.message || 'Unable to load portfolio dashboard')
      return null
    } finally {
      if (requestId === requestRef.current) setLoading(false)
    }
  }, [datasetId, segment, cutoffDate])

  useEffect(() => {
    refresh()
    return () => {
      requestRef.current += 1
    }
  }, [refresh])

  return { data, loading, error, refresh }
}

export default usePortfolioDashboard
