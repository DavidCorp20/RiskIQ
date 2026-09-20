import { useMemo, useState } from 'react'

const PERIODS = [
  { id: 'month', label: 'Mensual', months: 1 },
  { id: 'quarter', label: 'Trimestral', months: 3 },
  { id: 'semester', label: 'Semestral', months: 6 },
  { id: 'year', label: 'Anual', months: 12 },
]

const num = value => Number.isFinite(Number(value)) ? Number(value) : 0

function dateOf(row) {
  const raw = row?.snapshot_date || row?.date || row?.as_of || row?.period
  const date = raw ? new Date(raw) : null
  return date && !Number.isNaN(date.getTime()) ? date : null
}

function keyFor(date, months) {
  const month = Math.floor(date.getUTCMonth() / months) * months
  return `${date.getUTCFullYear()}-${String(month + 1).padStart(2, '0')}`
}

function aggregate(rows, months) {
  const groups = new Map()
  rows.forEach(row => {
    const date = dateOf(row)
    if (!date) return
    const key = keyFor(date, months)
    const current = groups.get(key)
    if (!current || date > current._date) groups.set(key, { ...row, _date: date, _key: key })
  })
  return [...groups.values()].sort((a, b) => a._date - b._date)
}

export function usePortfolioHistory(history) {
  const [period, setPeriod] = useState('month')
  const [thresholds, setThresholds] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('riskiq.healthThresholds') || 'null') || {
        par30: 0.05,
        par60: 0.03,
        par90: 0.02,
      }
    } catch {
      return { par30: 0.05, par60: 0.03, par90: 0.02 }
    }
  })

  const model = useMemo(() => {
    const config = PERIODS.find(item => item.id === period) || PERIODS[0]
    const rows = aggregate(history?.snapshots || [], config.months)
    const current = rows.at(-1) || null
    const previous = rows.at(-2) || null

    const metric = (row, key) => num(row?.[key] ?? row?.[`${key}_ratio`])
    const delta = key => {
      if (!current || !previous) return null
      return metric(current, key) - metric(previous, key)
    }

    return {
      period,
      periodLabel: config.label,
      rows,
      current,
      previous,
      delta,
      series: {
        exposure: rows.map(row => metric(row, 'outstanding_balance') || metric(row, 'exposure') || metric(row, 'balance')),
        par30: rows.map(row => metric(row, 'par30')),
        par60: rows.map(row => metric(row, 'par60')),
        par90: rows.map(row => metric(row, 'par90')),
      },
      comparable: rows.length >= 2,
    }
  }, [history, period])

  const updateThreshold = (key, value) => {
    const next = { ...thresholds, [key]: Math.max(0, num(value)) }
    setThresholds(next)
    try { localStorage.setItem('riskiq.healthThresholds', JSON.stringify(next)) } catch {}
  }

  const health = key => {
    const value = num(model.current?.[key])
    const limit = num(thresholds[key])
    if (!model.current) return 'unknown'
    return value > limit ? 'breach' : value > limit * 0.8 ? 'watch' : 'healthy'
  }

  return { ...model, periods: PERIODS, thresholds, updateThreshold, health }
}
