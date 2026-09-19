import React, { useMemo, useState } from 'react'
import { usePortfolioDashboard } from '../hooks/usePortfolioDashboard'
import PortfolioToolbar from './PortfolioToolbar'
import PortfolioKpiGrid from './PortfolioKpiGrid'
import RatingDistribution from './RatingDistribution'
import ExposureHeatmap from './ExposureHeatmap'
import VintageMatrix from './VintageMatrix'
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
  const { data, loading, error, refresh } = usePortfolioDashboard(datasetId, { segment, cutoffDate })

  const toolbar = data?.filters || {}
  const kpis = data?.kpis || {}
  const structure = data?.structure || {}
  const concentration = data?.concentration || {}
  const vintage = data?.vintage || {}
  const drivers = data?.riskDrivers || data?.risk_drivers || []

  const exportPayload = useMemo(() => ({
    contract_version: data?.contract_version || 'portfolio-dashboard-v1',
    dataset_id: datasetId,
    filters: { segment, cutoffDate },
    evidence: data || null
  }), [data, datasetId, segment, cutoffDate])

  if (!datasetId) {
    return (
      <section className="portfolio-dashboard portfolio-dashboard-empty">
        <div className="portfolio-empty-state">
          <span>PORTFOLIO DASHBOARD</span>
          <h2>No portfolio selected</h2>
          <p>Select an active dataset to load deterministic portfolio evidence.</p>
        </div>
      </section>
    )
  }

  return (
    <section className="portfolio-dashboard">
      <PortfolioToolbar
        segment={segment}
        segments={toolbar.segments || []}
        cutoffDate={cutoffDate}
        cutoffDates={toolbar.cutoffDates || []}
        onSegmentChange={setSegment}
        onCutoffDateChange={setCutoffDate}
        onRefresh={refresh}
        onExport={() => downloadJson(exportPayload, datasetId)}
        onRiskAnalysis={() => onRiskAnalysis?.(data)}
        loading={loading}
        disabled={!datasetId}
      />

      {loading && (
        <div className="portfolio-loading" role="status">
          <span className="portfolio-skeleton portfolio-skeleton-wide" />
          <span className="portfolio-skeleton" />
          <span className="portfolio-skeleton" />
        </div>
      )}

      {error && !loading && (
        <div className="portfolio-error" role="alert">
          <strong>Unable to load portfolio evidence.</strong>
          <span>{error}</span>
          <button type="button" onClick={refresh}>Retry</button>
        </div>
      )}

      {!loading && !error && data && (
        <>
          <PortfolioKpiGrid kpis={kpis} />

          <div className="portfolio-dashboard-grid">
            <RatingDistribution data={structure.ratingDistribution || []} />
            <ExposureHeatmap data={concentration.heatmap || concentration.items || []} />
          </div>

          <VintageMatrix
            rows={vintage.rows || []}
            columns={vintage.columns || []}
          />

          <section className="portfolio-panel">
            <div className="portfolio-panel-heading">
              <div><span>RISK DRIVERS</span><h3>Recorded drivers</h3></div>
              <small>{drivers.length} drivers</small>
            </div>
            {!drivers.length ? (
              <div className="portfolio-empty">No deterministic risk drivers available.</div>
            ) : (
              <div className="portfolio-drivers">
                {drivers.map((driver, index) => (
                  <article key={driver.id ?? driver.code ?? index}>
                    <div>
                      <strong>{driver.label ?? driver.name ?? driver.code ?? `Driver ${index + 1}`}</strong>
                      <span>{driver.description ?? driver.rationale ?? 'Recorded deterministic evidence.'}</span>
                    </div>
                    <b>{driver.displayValue ?? driver.value ?? '—'}</b>
                  </article>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </section>
  )
}
