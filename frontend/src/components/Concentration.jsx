import React, { useMemo } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import './concentration.css'

const money = (value) => {
  if (value == null || value === '') return '—'
  return `$${Number(value).toLocaleString(undefined, { maximumFractionDigits: 0 })}`
}

const pct = (value) => {
  if (value == null || value === '') return '—'
  return `${(Number(value) * 100).toFixed(1)}%`
}

const numeric = (value) => {
  const n = Number(value)
  return Number.isFinite(n) ? n : 0
}

export default function Concentration({ data = [], title = 'Concentración de riesgo', bad30 }) {
  const rows = useMemo(() => (Array.isArray(data) ? data : []).slice(0, 8), [data])

  if (!rows.length) {
    return (
      <section className="concentration-panel">
        <div className="concentration-empty">
          <span>CONCENTRATION</span>
          <strong>No hay evidencia de concentración suficiente.</strong>
          <p>RiskIQ necesita una dimensión de segmentación disponible en la cartera para localizar materialidad y deterioro.</p>
        </div>
      </section>
    )
  }

  const chartData = rows.map((item, index) => ({
    name: item.name || item.segment || item.label || `Segmento ${index + 1}`,
    exposure: numeric(item.exposure ?? item.outstanding_balance ?? item.balance),
    par30: numeric(item.par30 ?? item.metrics?.par30),
  }))

  return (
    <section className="concentration-panel">
      <header className="concentration-header">
        <div>
          <span>CONCENTRATION</span>
          <h3>{title}</h3>
          <p>Materialidad económica y deterioro observados en la evidencia determinística.</p>
        </div>
        {bad30 != null && <div className="concentration-total"><small>MORA 30+ TOTAL</small><strong>{money(bad30)}</strong></div>}
      </header>

      <div className="concentration-chart">
        <ResponsiveContainer width="100%" height={Math.max(280, rows.length * 48)}>
          <BarChart data={chartData} layout="vertical" margin={{ top: 8, right: 20, left: 12, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e7eb" />
            <XAxis xAxisId="exposure" type="number" tickFormatter={money} stroke="#94a3b8" tick={{ fontSize: 10 }} />
            <XAxis xAxisId="par30" type="number" orientation="top" domain={[0, 1]} tickFormatter={pct} stroke="#94a3b8" tick={{ fontSize: 10 }} />
            <YAxis type="category" dataKey="name" width={118} stroke="#64748b" tick={{ fontSize: 10 }} />
            <Tooltip
              formatter={(value, name) => name === 'PAR30' ? [pct(value), name] : [money(value), 'Exposición']}
              labelFormatter={(label) => `Segmento: ${label}`}
              contentStyle={{ borderRadius: 10, border: '1px solid #dbe3ea', boxShadow: '0 8px 24px rgba(15,23,42,.08)' }}
            />
            <Bar xAxisId="exposure" dataKey="exposure" name="Exposición" fill="#334155" radius={[0, 4, 4, 0]} barSize={12} />
            <Bar xAxisId="par30" dataKey="par30" name="PAR30" fill="#c2414a" radius={[0, 4, 4, 0]} barSize={7} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="concentration-table-wrap">
        <table className="concentration-table">
          <thead><tr><th>Segmento</th><th>Exposición</th><th>Share</th><th>PAR30</th><th>Contribución mora</th></tr></thead>
          <tbody>
            {rows.map((item, index) => (
              <tr key={item.id || item.name || index}>
                <th>{item.name || item.segment || item.label || `Segmento ${index + 1}`}</th>
                <td>{money(item.exposure ?? item.outstanding_balance ?? item.balance)}</td>
                <td>{pct(item.exposure_share ?? item.share_of_exposure)}</td>
                <td className="concentration-risk">{pct(item.par30 ?? item.metrics?.par30)}</td>
                <td>{pct(item.contribution_to_portfolio_bad_30 ?? item.contribution_to_portfolio_bad30)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
