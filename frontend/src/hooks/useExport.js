import { useCallback, useMemo } from 'react'

const escapeCsv = value => {
  if (value == null) return ''
  const text = typeof value === 'object' ? JSON.stringify(value) : String(value)
  return /[",\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text
}

const flatten = (value, prefix = '', out = {}) => {
  if (value == null) { out[prefix] = ''; return out }
  if (Array.isArray(value)) { out[prefix] = JSON.stringify(value); return out }
  if (typeof value !== 'object') { out[prefix] = value; return out }
  Object.entries(value).forEach(([key, child]) => flatten(child, prefix ? prefix + '.' + key : key, out))
  return out
}

const normalizeRows = rows => (Array.isArray(rows) ? rows : []).map(row => flatten(row))

export function useExport(defaultName = 'riskiq-report') {
  const csv = useCallback((rows, filename = defaultName) => {
    const normalized = normalizeRows(rows)
    const columns = [...new Set(normalized.flatMap(row => Object.keys(row)))]
    const body = [columns.map(escapeCsv).join(','), ...normalized.map(row => columns.map(column => escapeCsv(row[column])).join(','))].join('\n')
    const blob = new Blob(['\uFEFF' + body], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename.endsWith('.csv') ? filename : filename + '.csv'
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  }, [defaultName])

  const printPdf = useCallback((title = 'RiskIQ Executive Report') => {
    const previous = document.title
    document.title = title
    window.print()
    window.setTimeout(() => { document.title = previous }, 500)
  }, [])

  return useMemo(() => ({ exportCsv: csv, exportPdf: printPdf }), [csv, printPdf])
}
