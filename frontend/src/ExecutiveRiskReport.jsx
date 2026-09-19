import React, { useEffect, useMemo, useState } from 'react'
import { getLatestBacktestEvidence, listDecisionRules, listPolicyVersions } from './api'
import { useRiskIntelligence } from './RiskIntelligenceProvider'
import EvidenceMethodology from './EvidenceMethodology'

const pct = value => `${(Number(value || 0) * 100).toFixed(1)}%`
const num = value => Number(value || 0).toLocaleString('en-US', { maximumFractionDigits: 2 })

export default function ExecutiveRiskReport() {
  const { dataset, result, loading, error, ews, ewsLoading, ewsError, riskIntelligence } = useRiskIntelligence()
  const datasetId = dataset?.dataset_id || ''
  const [rules, setRules] = useState([])
  const [policy, setPolicy] = useState(null)
  const [backtest, setBacktest] = useState(null)

  useEffect(() => {
    let live = true

    ;(async () => {
      if (!datasetId) {
        setRules([])
        setPolicy(null)
        setBacktest(null)
        return
      }

      try {
        const ruleResult = await listDecisionRules(datasetId)
        if (!live) return

        const items = ruleResult?.items || []
        setRules(items)

        if (!items[0]?.id) {
          setPolicy(null)
          setBacktest(null)
          return
        }

        try {
          const versionsResult = await listPolicyVersions(items[0].id, datasetId)
          if (!live) return

          const versions = versionsResult?.versions || []
          const current = versions.at(-1) || null
          setPolicy(current)

          if (current?.version != null) {
            const evidence = await getLatestBacktestEvidence(
              datasetId,
              items[0].id,
              current.version
            )

            if (!live) return
            setBacktest(
              evidence?.recorded
                ? evidence.result || { summary: evidence.summary || {} }
                : null
            )
          } else {
            setBacktest(null)
          }
        } catch {
          if (live) {
            setPolicy(null)
            setBacktest(null)
          }
        }
      } catch {
        if (live) {
          setRules([])
          setPolicy(null)
          setBacktest(null)
        }
      }
    })()

    return () => {
      live = false
    }
  }, [datasetId])

  const snapshot = result?.snapshot || {}
  const analysis = result?.analysis || result?.risk_analytics?.deterministic || {}
  const drivers = analysis.drivers || []
  const backtestRows = backtest?.summary || backtest?.metrics || backtest || {}
  const ewsPortfolio = ews?.portfolio || {}
  const ewsTrend = ews?.trends?.par30 || {}
  const ewsAlerts = ews?.top_alerts || []

  const position = useMemo(
    () => [
      ['Exposure', snapshot.outstanding_balance != null ? num(snapshot.outstanding_balance) : '—', 'Current portfolio exposure'],
      ['Loans', snapshot.active_loans != null ? num(snapshot.active_loans) : '—', 'Records included in the run'],
      ['PAR30', snapshot.par30 != null ? pct(snapshot.par30) : '—', '30+ days past due'],
      ['PAR90', snapshot.par90 != null ? pct(snapshot.par90) : '—', '90+ days past due']
    ],
    [snapshot]
  )

  const exportReport = () => {
    const lines = [
      'RISKIQ · EXECUTIVE RISK REPORT',
      '',
      `Dataset: ${datasetId || '—'}`,
      `Generated: ${new Date().toISOString()}`,
      '',
      'RISK POSITION',
      ...position.map(item => `${item[0]}: ${item[1]} — ${item[2]}`),
      '',
      'RISK DRIVERS',
      ...(drivers.slice(0, 5).map((driver, index) =>
        `${index + 1}. ${driver.label || driver.name || driver.driver || 'Risk driver'}${driver.value != null ? ` · ${num(driver.value)}` : ''}`
      ) || ['No deterministic drivers recorded.']),
      '',
      'DECISION & POLICY',
      `Policy: ${policy?.name || rules[0]?.name || 'No policy selected'}`,
      `Version: ${policy?.version != null ? `v${policy.version}` : '—'}`,
      `Lifecycle: ${policy?.status || '—'}`,
      'Decision control: Human review required',
      '',
      'EARLY WARNING EVIDENCE',
      `High EWS exposure: ${num(ewsPortfolio.high_ews_exposure)}`,
      `High EWS exposure share: ${ewsPortfolio.high_ews_exposure_share != null ? pct(ewsPortfolio.high_ews_exposure_share) : '—'}`,
      `PAR30 trend: ${ewsTrend.ratio_delta != null ? pct(ewsTrend.ratio_delta) : '—'} · ${ewsTrend.direction || '—'}`,
      `Prioritized alerts: ${ewsAlerts.length}`,
      '',
      'BACKTEST EVIDENCE',
      `Recorded result: ${backtest ? 'Available' : 'Not recorded'}`,
      `Coverage: ${backtestRows.outcome_coverage != null ? pct(backtestRows.outcome_coverage) : '—'}`,
      `Accuracy: ${backtestRows.accuracy != null ? pct(backtestRows.accuracy) : '—'}`,
      `Bad rate: ${backtestRows.bad_rate != null ? pct(backtestRows.bad_rate) : '—'}`,
      '',
      'GOVERNANCE',
      'This report presents recorded deterministic evidence only.'
    ].join('\n')

    const blob = new Blob([lines], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `riskiq-executive-risk-report-${datasetId || 'portfolio'}.txt`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  if (!datasetId) {
    return (
      <section className="ri-exec-report">
        <div className="ri-exec-empty">
          <b>No portfolio selected</b>
          <span>Select an active portfolio before generating the executive report.</span>
        </div>
      </section>
    )
  }

  return (
    <section className="ri-exec-report">
      <header className="ri-exec-head">
        <div>
          <div className="ri-exec-kicker">RISKIQ · EXECUTIVE RISK REPORT</div>
          <h2>Portfolio risk position</h2>
          <p>
            Board-ready evidence assembled from the same global portfolio state used by
            the Risk Operating System.
          </p>
        </div>
        <div className="ri-exec-actions">
          <span className="ri-exec-status">
            {error ? 'EVIDENCE UNAVAILABLE' : loading ? 'REFRESHING EVIDENCE' : 'DETERMINISTIC EVIDENCE'}
          </span>
          <button onClick={exportReport}>Export report</button>
        </div>
      </header>

      {error && <div className="ri-exec-alert">{error}</div>}

      <div className="ri-exec-meta">
        <div><span>PORTFOLIO</span><b>{datasetId}</b></div>
        <div><span>POLICY</span><b>{policy?.name || rules[0]?.name || 'Not configured'}</b></div>
        <div><span>LIFECYCLE</span><b>{policy?.status || '—'}</b></div>
        <div><span>CONTROL</span><b>Human review required</b></div>
      </div>

      <div className="ri-exec-grid">
        {position.map(([label, value, detail]) => (
          <article key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{detail}</small>
          </article>
        ))}
      </div>

      <div className="ri-exec-columns">
        <article className="ri-exec-panel">
          <div className="ri-exec-panel-head">
            <div><span>RISK DRIVERS</span><h3>What requires attention</h3></div>
            <b>{drivers.length} recorded</b>
          </div>
          {drivers.length ? (
            <ol>
              {drivers.slice(0, 5).map((driver, index) => (
                <li key={index}>
                  <strong>{driver.label || driver.name || driver.driver || `Driver ${index + 1}`}</strong>
                  <span>
                    {driver.value != null ? num(driver.value) : driver.description || 'Recorded deterministic driver'}
                  </span>
                </li>
              ))}
            </ol>
          ) : (
            <p className="ri-exec-muted">No deterministic risk drivers were recorded.</p>
          )}
        </article>

        <article className="ri-exec-panel">
          <div className="ri-exec-panel-head">
            <div><span>DECISION & POLICY</span><h3>Controlled decision path</h3></div>
            <b>{policy?.status || 'NOT CONFIGURED'}</b>
          </div>
          <div className="ri-exec-evidence">
            <div><span>Policy</span><strong>{policy?.name || rules[0]?.name || 'Not configured'}</strong></div>
            <div><span>Version</span><strong>{policy?.version != null ? `v${policy.version}` : '—'}</strong></div>
            <div><span>Lifecycle</span><strong>{policy?.status || '—'}</strong></div>
            <div><span>Review</span><strong>Human review required</strong></div>
          </div>
        </article>
      </div>

      <EvidenceMethodology compact/><article className="ri-exec-panel"><div className="ri-exec-panel-head"><div><span>UNIFIED RISK INTELLIGENCE</span><h3>Predictive and event evidence</h3></div><b>{riskIntelligence?.evidence_hash ? 'GROUNDED' : 'WAITING'}</b></div><div className="ri-exec-grid ri-exec-mini"><article><span>PD ratings</span><strong>{riskIntelligence?.predictive?.pd_ratings?.length || 0}</strong></article><article><span>Risk events</span><strong>{riskIntelligence?.risk_events?.events?.length || 0}</strong></article><article><span>Stress scenarios</span><strong>{riskIntelligence?.stress_testing?.scenarios?.length || 0}</strong></article></div></article>
      <article className="ri-exec-panel"><div className="ri-exec-panel-head"><div><span>EARLY WARNING SYSTEM</span><h3>Portfolio deterioration signals</h3></div><b>{ewsLoading ? 'CALCULATING' : ewsError ? 'UNAVAILABLE' : 'DETERMINISTIC'}</b></div><div className="ri-exec-grid ri-exec-mini"><article><span>High EWS exposure</span><strong>{ewsPortfolio.high_ews_exposure == null ? '—' : num(ewsPortfolio.high_ews_exposure)}</strong></article><article><span>Exposure share</span><strong>{ewsPortfolio.high_ews_exposure_share == null ? '—' : pct(ewsPortfolio.high_ews_exposure_share)}</strong></article><article><span>PAR30 Δ</span><strong>{ewsTrend.ratio_delta == null ? '—' : pct(ewsTrend.ratio_delta)}</strong></article></div>{ewsError ? <p className="ri-exec-muted">{ewsError}</p> : <p className="ri-exec-muted">Signals are weighted by exposure and based on observed portfolio trajectories. They are not predictive probabilities.</p>}</article>
      <article className="ri-exec-panel ri-exec-backtest">
        <div className="ri-exec-panel-head">
          <div><span>BACKTEST EVIDENCE</span><h3>Historical validation</h3></div>
          <b>{backtest ? 'RECORDED' : 'NOT RECORDED'}</b>
        </div>
        {backtest ? (
          <div className="ri-exec-grid ri-exec-mini">
            <article><span>Coverage</span><strong>{backtestRows.outcome_coverage == null ? '—' : pct(backtestRows.outcome_coverage)}</strong></article>
            <article><span>Accuracy</span><strong>{backtestRows.accuracy == null ? '—' : pct(backtestRows.accuracy)}</strong></article>
            <article><span>Bad rate</span><strong>{backtestRows.bad_rate == null ? '—' : pct(backtestRows.bad_rate)}</strong></article>
          </div>
        ) : (
          <p className="ri-exec-muted">
            No matching recorded backtest result is available. RiskIQ does not manufacture validation claims.
          </p>
        )}
      </article>

      <footer className="ri-exec-foot">
        <div>
          <b>Executive recommendation</b>
          <span>
            Prioritize human review using recorded risk position, drivers and policy controls.
            Any approval or deployment decision remains subject to governance.
          </span>
        </div>
        <span>Generated {new Date().toLocaleString()}</span>
      </footer>

      <style>{`.ri-exec-report{display:flex;flex-direction:column;gap:18px}.ri-exec-head{display:flex;justify-content:space-between;gap:24px;padding:26px 28px;border:1px solid #dce3ea;border-radius:16px;background:#fff}.ri-exec-kicker,.ri-exec-panel-head>div>span{font-size:10px;letter-spacing:.14em;font-weight:800;color:#637083}.ri-exec-head h2{margin:5px 0 7px;font-size:28px;color:#172334}.ri-exec-head p{margin:0;color:#687789}.ri-exec-actions{display:flex;align-items:flex-start;gap:10px}.ri-exec-actions button{border:0;border-radius:9px;padding:10px 14px;background:#172334;color:#fff;font-weight:700;cursor:pointer}.ri-exec-status{padding:9px 10px;border:1px solid #dce3ea;border-radius:9px;font-size:10px;font-weight:800;color:#536274;white-space:nowrap}.ri-exec-meta{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:#dce3ea;border:1px solid #dce3ea;border-radius:14px;overflow:hidden}.ri-exec-meta div{background:#fff;padding:15px 17px;display:flex;flex-direction:column;gap:5px}.ri-exec-meta span{font-size:9px;font-weight:800;letter-spacing:.12em;color:#7a8796}.ri-exec-meta b{font-size:13px;color:#233246;overflow:hidden;text-overflow:ellipsis}.ri-exec-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.ri-exec-grid article{background:#fff;border:1px solid #dce3ea;border-radius:14px;padding:18px}.ri-exec-grid span{display:block;font-size:10px;font-weight:800;letter-spacing:.1em;color:#718094}.ri-exec-grid strong{display:block;margin:8px 0 5px;font-size:27px;color:#172334}.ri-exec-grid small{color:#718094}.ri-exec-columns{display:grid;grid-template-columns:1fr 1fr;gap:14px}.ri-exec-panel{background:#fff;border:1px solid #dce3ea;border-radius:14px;padding:20px}.ri-exec-panel-head{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:15px}.ri-exec-panel-head h3{margin:5px 0 0;font-size:17px;color:#1d2b3c}.ri-exec-panel-head>b{font-size:10px;color:#69788a}.ri-exec-panel ol{margin:0;padding-left:23px}.ri-exec-panel li{padding:10px 0;border-bottom:1px solid #edf0f3}.ri-exec-panel li:last-child{border-bottom:0}.ri-exec-panel li strong{display:block;color:#27374a}.ri-exec-panel li span{display:block;margin-top:3px;color:#718094;font-size:12px}.ri-exec-evidence{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:#e5e9ee}.ri-exec-evidence div{background:#fff;padding:12px}.ri-exec-evidence span{display:block;font-size:10px;color:#718094}.ri-exec-evidence strong{display:block;margin-top:4px;color:#25364a}.ri-exec-backtest{padding-bottom:22px}.ri-exec-mini{grid-template-columns:repeat(3,1fr);margin-top:5px}.ri-exec-mini article{padding:14px}.ri-exec-mini strong{font-size:22px}.ri-exec-muted{color:#718094;font-size:13px}.ri-exec-foot{display:flex;justify-content:space-between;gap:20px;padding:17px 20px;border:1px solid #dce3ea;border-radius:14px;background:#f7f9fb}.ri-exec-foot div{display:flex;flex-direction:column;gap:4px}.ri-exec-foot b{font-size:12px;color:#233246}.ri-exec-foot span{font-size:12px;color:#657487}.ri-exec-alert{padding:12px 15px;border:1px solid #e6d7b0;border-radius:10px;background:#fffaf0;color:#765c20}.ri-exec-empty{min-height:240px;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:8px;border:1px dashed #cfd8e2;border-radius:14px;color:#687789}.ri-exec-empty b{color:#25364a}@media(max-width:900px){.ri-exec-head,.ri-exec-columns{display:grid;grid-template-columns:1fr}.ri-exec-meta,.ri-exec-grid{grid-template-columns:1fr 1fr}.ri-exec-actions{justify-content:flex-start}}`}</style>
    </section>
  )
}
