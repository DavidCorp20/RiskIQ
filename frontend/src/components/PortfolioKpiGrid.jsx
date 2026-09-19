import React from 'react'

const KPI_ITEMS = [
  ['exposure', 'Total exposure'],
  ['active_loans', 'Active loans'],
  ['par30', 'PAR30'],
  ['par60', 'PAR60'],
  ['par90', 'PAR90'],
  ['npl', 'NPL'],
]

export default function PortfolioKpiGrid({ kpis = {} }) {
  return (
    <div className="portfolio-kpi-grid">
      {KPI_ITEMS.map(([key, label]) => {
        const metric = kpis[key]

        return (
          <article className="portfolio-kpi-card" key={key}>
            <span>{label}</span>
            <strong>{metric?.formatted ?? '—'}</strong>
            <small>{metric?.subtext ?? ''}</small>
          </article>
        )
      })}
    </div>
  )
}
