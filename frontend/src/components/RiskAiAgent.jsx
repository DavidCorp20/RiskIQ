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

function localAnswer(question, context) {
  const q = String(question).toLowerCase()
  if (/par\s*30|30\+|mora 30/.test(q)) {
    return `PAR30 es ${pct(context.par30)}, equivalente a ${money(context.exposure * context.par30)} sobre ${money(context.exposure)} de exposición.`
  }
  if (/par\s*60|60\+|mora 60/.test(q)) {
    return `PAR60 es ${pct(context.par60)}, equivalente a ${money(context.exposure * context.par60)} sobre ${money(context.exposure)} de exposición.`
  }
  if (/par\s*90|90\+|mora 90/.test(q)) {
    return `PAR90 es ${pct(context.par90)}, equivalente a ${money(context.exposure * context.par90)} sobre ${money(context.exposure)} de exposición.`
  }
  if (/expos|saldo|balance/.test(q)) {
    return `La exposición total calculada es ${money(context.exposure)}. PAR30 ${pct(context.par30)}, PAR60 ${pct(context.par60)} y PAR90 ${pct(context.par90)}.`
  }
  if (/deterior|empeor|migration|migraci|roll/.test(q)) {
    const driver = context.drivers[0]
    return driver
      ? `El principal driver disponible es ${driver.segment || driver.name || 'el segmento identificado'}, con la evidencia de transición calculada disponible.`
      : 'No hay evidencia histórica suficiente para afirmar una velocidad de deterioro. RiskIQ no inventa una tendencia con un único corte.'
  }
  const priority = context.priorities[0]?.title || 'la primera señal priorizada'
  return `La postura actual es ${context.posture}. La primera señal disponible es ${priority}. Revisa la evidencia calculada antes de tomar una acción.`
}

function Evidence({ items }) {
  if (!Array.isArray(items) || items.length === 0) return null
  return (
    <div className="mt-3 border-t border-slate-200 pt-3">
      <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">Evidencia calculada</div>
      <div className="space-y-1 text-xs leading-5 text-slate-600">
        {items.map((item, index) => (
          <div key={`evidence-${index}`}>{typeof item === 'string' ? item : JSON.stringify(item)}</div>
        ))}
      </div>
    </div>
  )
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
        content: localAnswer(question, context),
        evidence: [],
        source: error?.message || 'RiskIQ Evidence Fallback',
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
    <div className="min-h-[calc(100vh-145px)] w-full overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <header className="flex items-center justify-between border-b border-slate-200 px-5 py-5 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-900 text-white"><Bot size={20} /></div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">RISK AI AGENT</div>
            <h2 className="text-xl font-semibold tracking-tight text-slate-900">AI Risk Copilot</h2>
            <p className="text-sm text-slate-500">Respuestas fundamentadas en evidencia calculada.</p>
          </div>
        </div>
        {onClose ? <button type="button" onClick={onClose} className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-600">Cerrar</button> : null}
      </header>

      <div className="grid grid-cols-3 divide-x divide-slate-200 border-b border-slate-200">
        <div className="p-4"><div className="text-[10px] font-semibold uppercase text-slate-400">PAR30</div><div className="mt-1 text-lg font-semibold text-slate-900">{pct(context.par30)}</div></div>
        <div className="p-4"><div className="text-[10px] font-semibold uppercase text-slate-400">PAR60</div><div className="mt-1 text-lg font-semibold text-slate-900">{pct(context.par60)}</div></div>
        <div className="p-4"><div className="text-[10px] font-semibold uppercase text-slate-400">PAR90</div><div className="mt-1 text-lg font-semibold text-slate-900">{pct(context.par90)}</div></div>
      </div>

      <main className="min-h-[420px] space-y-4 overflow-y-auto bg-slate-50/50 p-4 sm:p-6">
        {messages.length === 0 ? (
          <div className="mx-auto flex min-h-[360px] max-w-2xl flex-col items-center justify-center text-center">
            <Sparkles size={26} className="mb-4 text-slate-700" />
            <h3 className="text-lg font-semibold text-slate-900">Pregunta sobre la cartera activa</h3>
            <p className="mt-1 text-sm text-slate-500">RiskIQ utiliza exposición, PAR30/60/90, prioridades y drivers calculados.</p>
            <div className="mt-5 grid w-full gap-2 sm:grid-cols-2">
              {prompts.map((prompt) => <button key={prompt} type="button" onClick={() => send(prompt)} className="rounded-lg border border-slate-200 bg-white p-3 text-left text-sm text-slate-700 hover:bg-slate-50">{prompt}</button>)}
            </div>
          </div>
        ) : null}

        {messages.map((message) => (
          <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[88%] rounded-xl border px-4 py-3 text-sm leading-6 shadow-sm ${message.role === 'user' ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white text-slate-700'}`}>
              <div className="whitespace-pre-wrap">{message.content}</div>
              {message.role !== 'user' ? <Evidence items={message.evidence} /> : null}
              {message.role !== 'user' ? <div className="mt-2 text-[10px] uppercase tracking-wider text-slate-400">{message.source}</div> : null}
            </div>
          </div>
        ))}
        {loading ? <div className="flex items-center gap-2 text-sm text-slate-500"><Activity size={15} className="animate-pulse" />Analizando evidencia…</div> : null}
      </main>

      <footer className="border-t border-slate-200 bg-white p-4">
        <div className="flex items-end gap-2 rounded-xl border border-slate-200 bg-white p-2">
          <textarea value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={onKeyDown} rows={2} placeholder="Pregunta sobre riesgo, mora, concentración o deterioro…" className="min-h-10 flex-1 resize-none border-0 bg-transparent px-2 py-2 text-sm text-slate-900 outline-none placeholder:text-slate-400" />
          <button type="button" onClick={() => send()} disabled={!input.trim() || loading} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-900 text-white disabled:cursor-not-allowed disabled:opacity-40" aria-label="Enviar consulta"><Send size={16} /></button>
        </div>
      </footer>
    </div>
  )
}
