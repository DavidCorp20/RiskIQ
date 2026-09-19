import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { getDatasetHistory, listDatasets, runDataset } from './api'

const RiskIntelligenceContext = createContext(null)

export function RiskIntelligenceProvider({ children }) {
  const [datasets, setDatasets] = useState([])
  const [dataset, setDataset] = useState(null)
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const datasetRef = useRef(null)

  useEffect(() => {
    datasetRef.current = dataset
  }, [dataset]

  const refreshDatasets = useCallback(async () => {
    const response = await listDatasets()
    const items = response?.datasets || response || []
    setDatasets(items)
    return items
  }, [])

  const executeDataset = useCallback(async (target = null) => {
    const active = target || datasetRef.current
    if (!active?.dataset_id) return null

    setLoading(true)
    setError('')

    try {
      const resultData = await runDataset(active.dataset_id)
      const historyData = await getDatasetHistory(active.dataset_id)
      setResult(resultData)
      setHistory(historyData)
      setDataset(current => ({
        ...(current || active),
        ...active,
        snapshot: resultData.snapshot
      }))
      localStorage.setItem('riskiq.activeDataset', JSON.stringify({
        ...active,
        snapshot: resultData.snapshot
      }))
      return resultData
    } catch (e) {
      setError(e.message || 'Unable to refresh portfolio evidence')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const selectDataset = useCallback(async (next) => {
    setDataset(next || null)
    setResult(null)
    setHistory(null)
    setError('')

    if (next?.dataset_id) {
      return executeDataset(next)
    }
    return null
  }, [executeDataset])

  useEffect(() => {
    let live = true

    ;(async () => {
      try {
        const items = await refreshDatasets()
        if (!live) return

        let saved = null
        try {
          saved = JSON.parse(localStorage.getItem('riskiq.activeDataset') || 'null')
        } catch {
          saved = null
        }

        const active =
          items.find(item => item.dataset_id === saved?.dataset_id) ||
          items[0] ||
          null

        if (active && live) {
          await executeDataset(active)
        }
      } catch (e) {
        if (live) setError(e.message || 'Unable to load RiskIQ portfolio state')
      }
    })()

    return () => {
      live = false
    }
  }, [executeDataset, refreshDatasets])

  const value = useMemo(() => ({
    datasets,
    dataset,
    result,
    history,
    loading,
    error,
    refreshDatasets,
    executeDataset,
    selectDataset,
    activeDatasetId: dataset?.dataset_id || ''
  }), [
    datasets,
    dataset,
    result,
    history,
    loading,
    error,
    refreshDatasets,
    executeDataset,
    selectDataset
  ])

  return (
    <RiskIntelligenceContext.Provider value={value}>
      {children}
    </RiskIntelligenceContext.Provider>
  )
}

export function useRiskIntelligence() {
  const context = useContext(RiskIntelligenceContext)
  if (!context) {
    throw new Error('useRiskIntelligence must be used inside RiskIntelligenceProvider')
  }
  return context
}
