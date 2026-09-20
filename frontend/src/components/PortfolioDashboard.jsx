import React, { useMemo, useState } from 'react'
import { usePortfolioDashboard } from '../hooks/usePortfolioDashboard'
import PortfolioToolbar from './PortfolioToolbar'
import PortfolioKpiGrid from './PortfolioKpiGrid'
import RatingDistribution from './RatingDistribution'
import ExposureHeatmap from './ExposureHeatmap'
import VintageMatrix from './VintageMatrix'
import Concentration from './Concentration'
import '../portfolio-dashboard.css'

const downloadJson = (data, datasetId) => {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `riskiq-portfolio-dashboard-${datasetId || 'portfolio'}.json`
  anchor.click()
  URL.revokeObjectURL(url)
}

export default function PortfolioDashboard({
  datasetId = '',
  onRiskAnalysis,
  initialSegment = '',
  initialCutoffDate = ''
}) {
  const [segment, setSegment] = useState(initialSegment)
  const [cutoffDate, setCutoffDate] = useState(initialCutoffDate)
  const { data: dashboard, loading, error, refresh } = usePortfolioDashboard(datasetId, { segment, cutoffDate })
  const filters = dashboard?.filters ?? {}

  const exportPayload = useMemo(() => ({
    contract_version: dashboard?.contract_version ?? 'portfolio-dashboard-v1',
    dataset_id: datasetId,
    filters: { segment, cutoffDate },
    evidence: dashboard ?? null
  }), [dashboard, datasetId, segment, cutoffDate])

  if (!datasetId) {
    return <section className="portfolio-dashboard portfolio-dashboard-empty">
      <div className="portfolio-empty-state">
        <span>PORTFOLIO DASHBOARD</span>
        <h2>No portfolio selected</h2>
        <p>Select an active dataset to load deterministic portfolio evidence.</p>
      </div>
    </section>
  }

  return <section className="portfolio-dashboard">
    <PortfolioToolbar
      segment={segment}
      segments={filters.segments}
      cutoffDate={cutoffDate}
      cutoffDates={filters.cutoff_dates}
      onSegmentChange={setSegment}
      onCutoffDateChange={setCutoffDate}
      onRefresh={refresh}
      onExport={() => downloadJson(exportPayload, datasetId)}
      onRiskAnalysis={() => onRiskAnalysis?.(dashboard)}
      loading={loading}
      disabled={!datasetId}
    />

    {loading && <div className="portfolio-loading" role="status">
      <span className="portfolio-skeleton portfolio-skeleton-wide" />
      <span className="portfolio-skeleton" />
      <span className="portfolio-skeleton" />
    </div>}

    {error && !loading && <div className="portfolio-error" role="alert">
      <strong>Unable to load portfolio evidence.</strong>
      <span>{error}</span>
      <button type="button" onClick={refresh}>Retry</button>
    </div>}

    {!loading && !error && dashboard && <>
      <PortfolioKpiGrid kpis={dashboard.kpis} />

      <div className="portfolio-dashboard-grid">
        <RatingDistribution data={dashboard.rating_distribution} />
        <ExposureHeatmap data={dashboard.heatmap} />
      </div>

      <Concentration data={dashboard.concentration?.segments || dashboard.concentration || []} />
      <VintageMatrix vintage={dashboard.vintage || []} />

      <section className="portfolio-panel">
        <div className="portfolio-panel-heading">
          <div><span>RISK DRIVERS</span><h3>Recorded drivers</h3></div>
          <small>{(dashboard.risk_drivers || []).length} drivers</small>
        </div>
        {!dashboard.risk_drivers?.length ? (
          <div className="portfolio-empty">No deterministic risk drivers available.</div>
        ) : (
          <div className="portfolio-drivers">
            {dashboard.risk_drivers.map((driver) => (
              <article key={driver.id}>
                <div><strong>{driver.name}</strong><span>{driver.description}</span></div>
                <b>{driver.value}</b>
              </article>
            ))}
          </div>
        )}
      </section>
    </>}
  </section>
}
