import React from 'react'

export default function ExposureHeatmap({ data = [], title = 'Exposure concentration' }) {
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
          {data.map((item) => (
            <div
              className="portfolio-heat-cell"
              key={item.id ?? `${item.row}:${item.column}`}
              style={{ '--risk-intensity': item.risk_intensity }}
            >
              <span>{item.label}</span>
              <strong>{item.formatted_exposure}</strong>
              <small>PAR30 {item.formatted_risk}</small>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
