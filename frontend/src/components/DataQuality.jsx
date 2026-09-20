import React from 'react'
import { AlertTriangle, CheckCircle2, Info } from 'lucide-react'
import './data-quality.css'

const pct = (value) => value == null ? '—' : `${(Number(value) * 100).toFixed(1)}%`

export default function DataQuality({ quality = {} }) {
  const score = quality.score ?? 0
  const checks = Array.isArray(quality.checks) ? quality.checks : []
  const status = quality.status || (score >= 90 ? 'passed' : score >= 70 ? 'warning' : 'blocked')

  return (
    <section className="dq-panel">
      <header className="dq-header">
        <div>
          <span>DATA QUALITY</span>
          <h3>Confianza analítica</h3>
          <p>La calidad determina qué evidencia puede utilizar RiskIQ sin asumir información que no existe.</p>
        </div>
        <div className={`dq-score dq-${status}`}>
          <strong>{score}/100</strong>
          <small>{status === 'passed' ? 'Lista para análisis' : status === 'warning' ? 'Análisis con limitaciones' : 'Análisis bloqueado'}</small>
        </div>
      </header>

      <div className="dq-grid">
        <article className="dq-card dq-confidence">
          <div className="dq-card-icon"><CheckCircle2 size={17} /></div>
          <div>
            <span>CONFIANZA ANALÍTICA</span>
            <strong>{quality.confidence || 'Evidencia determinística disponible'}</strong>
            <p>{quality.summary || 'RiskIQ separa la calidad de datos de la interpretación de riesgo para evitar conclusiones no sustentadas.'}</p>
          </div>
        </article>

        <article className="dq-card dq-limitations">
          <div className="dq-card-icon"><Info size={17} /></div>
          <div>
            <span>LIMITACIÓN CLAVE</span>
            <strong>Migration necesita múltiples snapshots</strong>
            <p>{quality.limitation || 'Un único corte permite medir el estado actual, pero no permite observar transiciones entre estados de DPD. Para Roll Rates y velocidad de deterioro se requieren al menos dos cortes comparables con la misma identidad de crédito.'}</p>
          </div>
        </article>
      </div>

      {checks.length > 0 && (
        <div className="dq-checks">
          {checks.map((check, index) => (
            <div className="dq-check" key={check.field || index}>
              <div><strong>{check.label || check.field || 'Control'}</strong><span>{pct(check.coverage)}</span></div>
              <small>{check.status || '—'}</small>
            </div>
          ))}
        </div>
      )}

      {status === 'blocked' && (
        <div className="dq-alert"><AlertTriangle size={16} /><span>Corrige las condiciones bloqueantes antes de utilizar esta cartera para decisiones de riesgo.</span></div>
      )}
    </section>
  )
}
