import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import useRiskCopilot from '../hooks/useRiskCopilot'

const RiskIntelligenceContext = createContext(null)

export function RiskIntelligenceProvider({ children }) {
  const [source, setSource] = useState({ result: null, datasetId: '' })

  const setRiskContext = useCallback((result, datasetId = '') => {
    setSource({
      result: result || null,
      datasetId: datasetId || result?.dataset_id || '',
    })
  }, [])

  const clearRiskContext = useCallback(() => {
    setSource({ result: null, datasetId: '' })
  }, [])

  const copilot = useRiskCopilot(source)

  const value = useMemo(() => ({
    ...copilot,
    result: source.result,
    datasetId: source.datasetId,
    setRiskContext,
    clearRiskContext,
  }), [copilot, source.result, source.datasetId, setRiskContext, clearRiskContext])

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

export default RiskIntelligenceProvider
