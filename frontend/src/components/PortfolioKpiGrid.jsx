import React from 'react'

const formatMoney = value => value == null ? '—' : new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0
}).format(Number(value))

const formatNumber = value => value == null ? '—' : new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 0
}).format(Number(value))

const formatPercent = value => value == null ? '—' : `${(Number(value) * 100).toFixed(1)}%`

export default function PortfolioKpiGrid({ kpis = {} }) {
  const items = [
    { key: 'exposure', label: 'Total exposure', value: formatMoney(kpis.exposure), detail: kpis.exposureLabel || 'Outstanding balance' },
    { key: 'loans', label: 'Active loans', value: formatNumber(kpis.activeLoans), detail: kpis.activeLoansLabel || 'Included in portfolio' },
    { key: 'par30', label: 'PAR30', value: formatPercent(kpis.par30), detail: '30+ DPD exposure' },
    { key: 'par60', label: 'PAR60', value: formatPercent(kpis.par60), detail: '60+ DPD exposure' },
    { key: 'par90', label: 'PAR90', value: formatPercent(kpis.par90), detail: '90+ DPD exposure' },
    { key: 'npl', label: 'NPL', value: formatPercent(kpis.npl), detail: 'Non-performing exposure' }
  ]

  return (
    <div className="portfolio-kpi-grid">
      {items.map(item => (
        <article className="portfolio-kpi-card" key={item.key}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
          <small>{item.detail}</small>
        </article>
      ))}
    </div>
  )
}
