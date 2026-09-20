import { useMemo, useState } from 'react'
import { Activity, Bot, Send, Sparkles } from 'lucide-react'
import { askCopilot } from '../api'

const pct = (value) => `${(Number(value || 0) * 100).toFixed(1)}%`
const money = (value) => `$${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`

function contextFrom(result, datasetId) {
  const snapshot = result?.snapshot || {}
  const risk = result?.risk_intelligence || {}
  const advanced = result?.advanced_analytics || {}
  return {
    datasetId: datasetId || '',
    exposure: Number(snapshot.outstanding_balance ?? risk.materiality?.exposure ?? result?.exposure ?? 0),
    par30: Number(snapshot.par30 || 0),
    par60: Number(snapshot.par60 || 0),
    par90: Number(snapshot.par90 || 0),
    posture: risk.posture?.label || risk.posture?.level || 'Sin clasificar',
    priorities: Array.isArray(risk.priorities) ? risk.priorities : [],
    drivers: Array.isArray(result?.deterioration_drivers)
      ? result.deterioration_drivers
      : Array.isArray(advanced.deterioration_drivers)
        ? advanced.deterioration_drivers
        : [],
  }
}

function Evidence({ items }) {
  if (!Array.isArray(items) || items.length === 0) return null
  return <div className="risk-ai-evidence">
    <div className="risk-ai-evidence-label">Evidencia calculada</div>
    {items.map((item, index) => <div key={`evidence-${index}`}>{typeof item === 'string' ? item : JSON.stringify(item)}</div>)}
  </div>
}

export default function RiskAiAgent({ result, datasetId, onClose }) {
  const context = useMemo(() => contextFrom(result, datasetId), [result, datasetId])
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)

  const prompts = ['¿Qué debería revisar primero?', '¿Dónde está concentrado el riesgo?', '¿Qué está deteriorando la cartera?', 'Explícame el PAR30']

  async function send(questionValue = '') {
    const question = String(questionValue || input).trim()
    if (!question || loading) return
    setMessages((current) => [...current, { id: `${Date.now()}-u`, role: 'user', content: question }])
    setInput('')
    setLoading(true)

    try {
      if (!context.datasetId) throw new Error('No hay una cartera activa para consultar.')
      const response = await askCopilot({
        question,
        dataset_id: context.datasetId,
        risk_facts: {
          dataset_id: context.datasetId,
          facts: {
            par30: { id: 'par30', label: 'PAR30', value: context.par30, unit: '' },
            par60: { id: 'par60', label: 'PAR60', value: context.par60, unit: '' },
            par90: { id: 'par90', label: 'PAR90', value: context.par90, unit: '' },
            exposure: { id: 'exposure', label: 'Exposición total', value: context.exposure, unit: '' },
          },
          summary: { status: context.posture },
        },
        drivers: context.drivers,
        decisions: context.priorities,
      })
      setMessages((current) => [...current, {
        id: `${Date.now()}-a`,
        role: 'agent',
        content: response?.answer || 'El backend no devolvió una respuesta interpretable.',
        evidence: response?.evidence || [],
        source: response?.provider || response?.mode || 'RiskIQ AI',
      }])
    } catch (error) {
      setMessages((current) => [...current, {
        id: `${Date.now()}-f`,
        role: 'agent',
        content: 'No se pudo consultar el Copilot en este momento. La evidencia determinística de la cartera sigue disponible en Risk Analytics.',
        evidence: [],
        source: error?.message || 'RiskIQ AI unavailable',
      }])
    } finally {
      setLoading(false)
    }
  }

  function onKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      send()
    }
  }

  return (
    <div className="risk-ai-shell">
      <header className="risk-ai-header">
        <div className="risk-ai-brand">
          <div className="risk-ai-icon"><Bot size={20} /></div>
          <div>
            <div className="risk-ai-kicker">RISK AI AGENT</div>
            <h2>AI Risk Copilot</h2>
            <p>Interpretación ejecutiva sobre evidencia calculada.</p>
          </div>
        </div>
        {onClose ? <button type="button" onClick={onClose} className="risk-ai-close">Cerrar</button> : null}
      </header>

      <section className="risk-ai-metrics">
        <Metric label="Exposición" value={money(context.exposure)} detail="Evidencia actual" />
        <Metric label="PAR30" value={pct(context.par30)} detail="30+ días" />
        <Metric label="PAR60" value={pct(context.par60)} detail="60+ días" />
        <Metric label="PAR90" value={pct(context.par90)} detail="90+ días" />
      </section>

      <main className="risk-ai-body">
        {messages.length === 0 && (
          <div className="risk-ai-empty">
            <Sparkles size={25} />
            <h3>Pregunta sobre la cartera activa</h3>
            <p>El Copilot cruza evidencia determinística únicamente cuando la consulta es analítica.</p>
            <div className="risk-ai-prompts">
              {prompts.map((prompt) => (
                <button key={prompt} type="button" onClick={() => send(prompt)}>{prompt}</button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div key={message.id} className={`risk-ai-message ${message.role === 'user' ? 'user' : 'agent'}`}>
            <div className="risk-ai-bubble">
              <div className="risk-ai-content">{message.content}</div>
              {message.role !== 'user' && <Evidence items={message.evidence} />}
              {message.role !== 'user' && <div className="risk-ai-source">{message.source}</div>}
            </div>
          </div>
        ))}
        {loading && <div className="risk-ai-loading"><Activity size={15} />Analizando evidencia…</div>}
      </main>

      <footer className="risk-ai-footer">
        <div className="risk-ai-input">
          <textarea value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={onKeyDown} rows={2} placeholder="Pregunta sobre riesgo, mora, concentración o deterioro…" />
          <button type="button" onClick={() => send()} disabled={!input.trim() || loading} aria-label="Enviar consulta"><Send size={16} /></button>
        </div>
      </footer>
    </div>
  )
}

function Metric({ label, value, detail }) {
  return <article className="risk-ai-metric">
    <span>{label}</span>
    <strong>{value}</strong>
    <small>{detail}</small>
  </article>
}
