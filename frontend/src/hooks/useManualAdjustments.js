import { useCallback, useMemo, useState } from 'react'

const storageKey = datasetId => 'riskiq.manualAdjustments.' + (datasetId || 'unknown')

export function useManualAdjustments(datasetId) {
  const [adjustments, setAdjustments] = useState(() => {
    try { return JSON.parse(localStorage.getItem(storageKey(datasetId)) || '[]') || [] } catch { return [] }
  })
  const persist = useCallback(next => { setAdjustments(next); try { localStorage.setItem(storageKey(datasetId), JSON.stringify(next)) } catch {} }, [datasetId])
  const upsertAdjustment = useCallback((row, changes, reason='') => {
    const id = String(row?.loan_id || row?.id || row?._id || '')
    if (!id) return
    const next = [...adjustments.filter(x => x.row_id !== id), { adjustment_id: id + '-' + Date.now(), row_id:id, changes:{...changes}, reason:reason || 'Reclasificación manual', actor:'user', created_at:new Date().toISOString() }]
    persist(next)
  }, [adjustments,persist])
  const removeAdjustment = useCallback(row => { const id=String(row?.loan_id || row?.id || row?._id || ''); persist(adjustments.filter(x=>x.row_id!==id)) }, [adjustments,persist])
  const applyAdjustments = useCallback(rows => rows.map(row => { const id=String(row?.loan_id || row?.id || row?._id || ''); const a=adjustments.find(x=>x.row_id===id); return a ? {...row,...a.changes,_manual_adjustment:a} : row }), [adjustments])
  return { adjustments, adjustedRows:useMemo(()=>adjustments.length,[adjustments]), upsertAdjustment, removeAdjustment, applyAdjustments }
}