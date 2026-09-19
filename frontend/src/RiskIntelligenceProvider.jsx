import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { getDatasetHistory, listDatasets, runDataset, getDecisionRecommendations, createDecisionRecommendation } from './api'
import { usePortfolioEWS } from './hooks/usePortfolioEWS'

const RiskIntelligenceContext = createContext(null)

export function RiskIntelligenceProvider({ children }) {
  const [datasets, setDatasets] = useState([])
  const [dataset, setDataset] = useState(null)
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [decisionRecommendations, setDecisionRecommendations] = useState([])
  const [decisionLoading, setDecisionLoading] = useState(false)
  const [decisionError, setDecisionError] = useState('')
  const datasetRef = useRef(null)
  const { data: ews, loading: ewsLoading, error: ewsError, refresh: refreshEWS } = usePortfolioEWS(dataset?.dataset_id || '')

  useEffect(() => {
    datasetRef.current = dataset
  }, [dataset])

  const refreshDatasets = useCallback(async () => {
    const response = await listDatasets()
    const items = response?.datasets || response || []
    setDatasets(items)
    return items
  }, [])

  const refreshDecisionRecommendations = useCallback(async (targetId = '') => {
    const id = targetId || datasetRef.current?.dataset_id || ''
    if (!id) { setDecisionRecommendations([]); return { items: [] } }
    setDecisionLoading(true)
    setDecisionError('')
    try {
      const response = await getDecisionRecommendations({ dataset_id: id, limit: 200 })
      const items = response?.items || []
      setDecisionRecommendations(items)
      return response
    } catch (e) {
      setDecisionError(e.message || 'Unable to load decision recommendations')
      throw e
    } finally {
      setDecisionLoading(false)
    }
  }, [])

  const createRecommendations = useCallback(async (payload = {}) => {
    const id = payload.dataset_id || datasetRef.current?.dataset_id || ''
    if (!id) return null
    const response = await createDecisionRecommendation({ ...payload, dataset_id: id })
    setDecisionRecommendations(response?.recommendations || [])
    return response
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
      await refreshDecisionRecommendations(active.dataset_id)
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
  }, [refreshDecisionRecommendations])

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
    activeDatasetId: dataset?.dataset_id || '',
    ews,
    ewsLoading,
    ewsError,
    refreshEWS,
    decisionRecommendations,
    decisionLoading,
    decisionError,
    refreshDecisionRecommendations,
    createRecommendations
  }), [
    datasets,
    dataset,
    result,
    history,
    loading,
    error,
    refreshDatasets,
    executeDataset,
    selectDataset,
    ews,
    ewsLoading,
    ewsError,
    refreshEWS,
    decisionRecommendations,
    decisionLoading,
    decisionError,
    refreshDecisionRecommendations,
    createRecommendations
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
