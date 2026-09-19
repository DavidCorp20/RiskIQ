import React from 'react'
import { BarChart3, Download, RefreshCw } from 'lucide-react'

export default function PortfolioToolbar({
  segment = '',
  segments = [],
  cutoffDate = '',
  cutoffDates = [],
  onSegmentChange,
  onCutoffDateChange,
  onRefresh,
  onExport,
  onRiskAnalysis,
  loading = false,
  disabled = false
}) {
  return (
    <div className="portfolio-toolbar">
      <div className="portfolio-toolbar-context">
        <div className="portfolio-toolbar-title">
          <span>PORTFOLIO DASHBOARD</span>
          <strong>Portfolio structure & risk evidence</strong>
        </div>
        <div className="portfolio-toolbar-filters">
          <label>
            <span>Segment</span>
            <select value={segment} onChange={e => onSegmentChange?.(e.target.value)} disabled={disabled}>
              <option value="">All segments</option>
              {segments.map(item => {
                const value = typeof item === 'string' ? item : item.value ?? item.name
                const label = typeof item === 'string' ? item : item.label ?? item.name ?? item.value
                return <option key={value} value={value}>{label}</option>
              })}
            </select>
          </label>
          <label>
            <span>Cutoff date</span>
            <select value={cutoffDate} onChange={e => onCutoffDateChange?.(e.target.value)} disabled={disabled}>
              <option value="">Latest available</option>
              {cutoffDates.map(date => <option key={date} value={date}>{date}</option>)}
            </select>
          </label>
        </div>
      </div>

      <div className="portfolio-toolbar-actions">
        <button type="button" onClick={onRefresh} disabled={disabled || loading} title="Refresh evidence">
          <RefreshCw size={15} className={loading ? 'portfolio-spin' : ''} />
          Refresh
        </button>
        <button type="button" onClick={onExport} disabled={disabled} title="Export dashboard evidence">
          <Download size={15} />
          Export
        </button>
        <button type="button" className="portfolio-toolbar-primary" onClick={onRiskAnalysis} disabled={disabled}>
          <BarChart3 size={15} />
          Risk Analysis
        </button>
      </div>
    </div>
  )
}
