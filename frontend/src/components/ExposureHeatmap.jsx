import React from 'react'

export default function ExposureHeatmap({ data = [], title = 'Exposure concentration' }) {
  const max = data.reduce((current, item) => Math.max(current, Number(item.intensity ?? item.exposure ?? 0)), 0)

  return (
    <section className="portfolio-panel">
      <div className="portfolio-panel-heading">
        <div><span>CONCENTRATION</span><h3>{title}</h3></div>
        <small>API-provided intensity</small>
      </div>
      {!data.length ? (
        <div className="portfolio-empty">No concentration evidence available.</div>
      ) : (
        <div className="portfolio-heatmap" role="table" aria-label={title}>
          {data.map((item, index) => {
            const intensity = Number(item.intensity ?? item.exposure ?? 0)
            const normalized = item.intensity != null ? Number(item.intensity) : (max ? intensity / max : 0)
            return (
              <div
                className="portfolio-heat-cell"
                key={item.id ?? item.label ?? index}
                style={{ '--risk-intensity': Math.max(0, Math.min(1, normalized)) }}
              >
                <span>{item.label ?? item.segment ?? item.name ?? '—'}</span>
                <strong>{item.displayValue ?? item.exposureLabel ?? item.exposure ?? '—'}</strong>
                {item.par30 != null && <small>PAR30 {(Number(item.par30) * 100).toFixed(1)}%</small>}
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}
