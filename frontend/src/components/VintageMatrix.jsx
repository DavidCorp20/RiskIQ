import React from 'react'
import './vintage-matrix.css'

const pct = (value) => value == null ? '—' : `${(Number(value) * 100).toFixed(1)}%`
const intensity = (value) => {
  const n = Number(value)
  return Number.isFinite(n) ? Math.max(0, Math.min(1, n)) : 0
}

function heatStyle(value) {
  const level = intensity(value)
  const hue = 145 - (level * 130)
  return {
    background: `hsl(${hue} 72% 94%)`,
    borderColor: `hsl(${hue} 52% 76%)`,
    color: `hsl(${hue} 48% 27%)`
  }
}

export default function VintageMatrix({ vintage = [], data = [], title = 'Vintage matrix' }) {
  const rows = Array.isArray(vintage) && vintage.length ? vintage : data

  return (
    <section className="portfolio-panel vintage-matrix">
      <div className="portfolio-panel-heading">
        <div><span>VINTAGE</span><h3>{title}</h3></div>
        <small>{rows.length} cohorts · risk intensity</small>
      </div>

      {!rows.length ? (
        <div className="portfolio-empty">No hay evidencia de Vintage disponible.</div>
      ) : (
        <div className="vintage-heatmap-wrap">
          <div className="vintage-heatmap-head"><span>Cohorte</span><span>PAR30</span><span>Exposure</span><span>Risk intensity</span></div>
          {rows.map((cell, index) => {
            const risk = cell.risk_intensity
            return (
              <div className="vintage-heat-row" key={cell.vintage || cell.period || index}>
                <strong>{cell.vintage || cell.period || '—'}</strong>
                <span>{cell.formatted_value ?? pct(cell.par30)}</span>
                <span>{cell.formatted_exposure ?? cell.exposure ?? '—'}</span>
                <span className="vintage-risk-cell" style={heatStyle(risk)}>
                  {risk == null ? '—' : pct(risk)}
                </span>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}
