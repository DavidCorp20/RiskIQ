import { useMemo, useState } from 'react'
import {
  Activity,
  Bot,
  Database,
  Send,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  X,
} from 'lucide-react'
import { askCopilot } from '../api'

const formatPercentage = (value) => `${(Number(value || 0) * 100).toFixed(1)}%`

const formatMoney = (value) => `$${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`

function getRiskContext(result, datasetId) {
  const snapshot = result?.snapshot || {}
  const risk = result?.risk_intelligence || {}
  const advanced = result?.advanced_analytics || {}
  const materiality = risk.materiality || {}
  const priorities = Array.isArray(risk.priorities) ? risk.priorities : []
  const concentration = Array.isArray(risk.concentration) ? risk.concentration : []
  const deteriorationDrivers = Array.isArray(result?.deterioration_drivers)
    ? result.deterioration_drivers
    : Array.isArray(advanced?.deterioration_drivers)
      ? advanced.deterioration_drivers
      : Array.isArray(result?.analysis?.drivers)
        ? result.analysis.drivers
        : []

  return {
    datasetId: datasetId || '',
    exposure: Number(snapshot.outstanding_balance ?? materiality.exposure ?? result?.exposure ?? 0),
    par30: Number(snapshot.par30 || 0),
    par60: Number(snapshot.par60 || 0),
    par90: Number(snapshot.par90 || 0),
    posture: risk.posture?.level || '',
    postureLabel: risk.posture?.label || risk.posture?.level || 'Sin clasificar',
    priorities,
    concentration,
    deteriorationDrivers,
  }
}

function findCriticalSegment(context) {
  const priority = context.priorities.find((item) => /segment/i.test(String(item?.title || '')))
  if (priority) return priority.title

  const top = context.concentration.reduce((best, item) => {
    if (!best) return item
    return Number(item?.exposure_share || 0) > Number(best?.exposure_share || 0) ? item : best
  }, null)

  return top?.name || 'No identificado'
}

function buildLocalAnswer(question, context) {
  const query = String(question || '').toLowerCase()
  const segment = findCriticalSegment(context)

  if (/segment|concentrad|cartera.*donde|donde.*riesgo|concentración/.test(query)) {
    const top = context.concentration[0]
    if (!top) return 'No hay una dimensión de concentración suficiente para identificar un segmento crítico con la evidencia disponible.'
    return `La mayor concentración de exposición está en ${top.name}, con ${formatPercentage(top.exposure_share)} de la cartera y PAR30 de ${formatPercentage(top.par30)}. La contribución a 30+ es ${formatPercentage(top.contribution_to_portfolio_bad_30)}. Conviene revisar este segmento junto con su deterioro y exposición.`
  }

  if (/deterior|empeor|migration|migraci|roll|velocidad|transición/.test(query)) {
    const driver = context.deteriorationDrivers[0]
    if (!driver) return 'No hay evidencia histórica suficiente para afirmar una velocidad de deterioro. Con un único corte, RiskIQ presenta un baseline y no inventa una tendencia.'
    const rate = driver.transition_rate_30plus != null ? formatPercentage(driver.transition_rate_30plus) : 'sin tasa de transición calculable'
    const name = driver.segment || driver.name || segment || 'un segmento'
    return `El principal driver disponible apunta a ${name}, con una tasa de transición a 30+ de ${rate}. Esta señal debe contrastarse con snapshots comparables antes de convertirla en una decisión.`
  }

  if (/par\s*30|30\+|mora 30/.test(query)) {
    return `PAR30 actual: ${formatPercentage(context.par30)}, equivalente a ${formatMoney(context.exposure * context.par30)} de exposición aproximada en 30+ sobre ${formatMoney(context.exposure)} de exposición total.`
  }

  if (/par\s*60|60\+|mora 60/.test(query)) {
    return `PAR60 actual: ${formatPercentage(context.par60)}, equivalente a ${formatMoney(context.exposure * context.par60)} de exposición aproximada en 60+ sobre ${formatMoney(context.exposure)} de exposición total.`
  }

  if (/par\s*90|90\+|mora 90/.test(query)) {
    return `PAR90 actual: ${formatPercentage(context.par90)}, equivalente a ${formatMoney(context.exposure * context.par90)} de exposición aproximada en 90+ sobre ${formatMoney(context.exposure)} de exposición total.`
  }

  if (/expos|saldo|balance|outstanding/.test(query)) {
    return `La exposición total calculada es ${formatMoney(context.exposure)}. PAR30 es ${formatPercentage(context.par30)}, PAR60 es ${formatPercentage(context.par60)} y PAR90 es ${formatPercentage(context.par90)}.`
  }

  if (/riesgo|estado|postura|prioridad|primero|revisar|alerta/.test(query)) {
    const firstPriority = context.priorities[0]?.title || segment || 'No identificada'
    return `La postura actual es ${context.postureLabel}. La primera señal priorizada es ${firstPriority}. Revisa la evidencia calculada asociada antes de tomar una acción.`
  }

  return `Con la evidencia disponible: exposición ${formatMoney(context.exposure)}, PAR30 ${formatPercentage(context.par30)}, PAR60 ${formatPercentage(context.par60)} y PAR90 ${formatPercentage(context.par90)}. Puedo ayudarte a interpretar deterioro, concentración, mora y prioridades.`
}

function riskTone(posture) {
  if (posture === 'critical' || posture === 'high') return 'border-red-200 bg-red-50 text-red-700'
  if (posture === 'watch') return 'border-amber-200 bg-amber-50 text-amber-700'
  return 'border-emerald-200 bg-emerald-50 text-emerald-700'
}

function Evidence({ items }) {
  if (!items?.length) return null

  return (
    <div className="mt-3 border-t border-slate-200 pt-3">
      <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Evidencia calculada</div>
      <div className="space-y-1">
        {items.map((item, index) => (
          <div key={`evidence-${index}`} className="text-xs leading-5 text-slate-600">
            {typeof item === 'string' ? item : JSON.stringify(item)}
          </div>
        ))}
      </div>
    </div>
  )
}

export default function RiskAiAgent({ result, datasetId, onClose }) {
  const context = useMemo(() => getRiskContext(result, datasetId), [result, datasetId])
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  const quickPrompts = [
    '¿Qué debería revisar primero?',
    '¿Dónde está concentrado el riesgo?',
    '¿Qué está deteriorando la cartera?',
    'Explícame el PAR30',
  ]

  async function handleSend(questionOverride = '') {
    const question = String(questionOverride || input || '').trim()
    if (!question || isAnalyzing) return

    setMessages((current) => [...current, { id: `${Date.now()}-user`, role: 'user', content: question }])
    setInput('')
    setIsAnalyzing(true)

    try {
      if (!context.datasetId) {
        throw Object.assign(new Error('No hay una cartera activa para consultar.'), { status: 400 })
      }

      const riskFacts = {
        dataset_id: context.datasetId,
        facts: {
          par30: { id: 'par30', label: 'PAR30', value: context.par30, unit: '' },
          par60: { id: 'par60', label: 'PAR60', value: context.par60, unit: '' },
          par90: { id: 'par90', label: 'PAR90', value: context.par90, unit: '' },
          exposure: { id: 'exposure', label: 'Exposición total', value: context.exposure, unit: '' },
        },
        summary: { status: context.posture || 'unknown' },
      }

      const response = await askCopilot({
        question,
        dataset_id: context.datasetId,
        risk_facts: riskFacts,
        drivers: context.deteriorationDrivers,
        decisions: context.priorities,
      })

      setMessages((current) => [
        ...current,
        {
          id: `${Date.now()}-agent`,
          role: 'agent',
          content: response?.answer || 'El backend no devolvió una respuesta interpretable.',
          evidence: Array.isArray(response?.evidence) ? response.evidence : [],
          decision: response?.decision || null,
          provider: response?.provider || response?.mode || 'RiskIQ AI',
          source: 'backend',
        },
      ])
    } catch (error) {
      const useFallback = !error?.status || Number(error.status) >= 500

      if (useFallback) {
        setMessages((current) => [
          ...current,
          {
            id: `${Date.now()}-fallback`,
            role: 'agent',
            content: buildLocalAnswer(question, context),
            evidence: [],
            provider: 'RiskIQ Evidence Fallback',
            source: 'local-fallback',
          },
        ])
      } else {
        setMessages((current) => [
          ...current,
          {
            id: `${Date.now()}-error`,
            role: 'agent',
            content: error?.message || 'No fue posible procesar la consulta.',
            evidence: [],
            provider: 'RiskIQ AI',
            source: 'backend-error',
          },
        ])
      }
    } finally {
      setIsAnalyzing(false)
    }
  }

  function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="min-h-[calc(100vh-145px)] w-full overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex min-h-[calc(100vh-145px)] flex-col lg:flex-row">
        <section className="flex min-w-0 flex-1 flex-col">
          <header className="flex flex-col gap-4 border-b border-slate-200 px-5 py-5 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-900 text-white">
                <Bot size={20} strokeWidth={1.5} />
              </div>
              <div className="min-w-0">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">RISK AI AGENT</div>
                <h2 className="truncate text-xl font-semibold tracking-tight text-slate-900">AI Risk Copilot</h2>
                <p className="mt-0.5 text-sm text-slate-500">Respuestas fundamentadas en evidencia calculada.</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className={`inline-flex w-fit items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-medium ${riskTone(context.posture)}`}>
                <span className="h-1.5 w-1.5 rounded-full bg-current" />
                {context.postureLabel}
              </span>
              {onClose && (
                <button type="button" onClick={onClose} aria-label="Cerrar Risk AI Agent" className="flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-500 transition hover:bg-slate-50 hover:text-slate-900">
                  <X size={15} strokeWidth={1.5} />
                </button>
              )}
            </div>
          </header>

          <div className="grid grid-cols-3 divide-x divide-slate-200 border-b border-slate-200 bg-white">
            <div className="px-4 py-3">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">PAR30</div>
              <div className="mt-1 text-lg font-semibold tabular-nums text-slate-900">{formatPercentage(context.par30)}</div>
            </div>
            <div className="px-4 py-3">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">PAR60</div>
              <div className="mt-1 text-lg font-semibold tabular-nums text-slate-900">{formatPercentage(context.par60)}</div>
            </div>
            <div className="px-4 py-3">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">PAR90</div>
              <div className="mt-1 text-lg font-semibold tabular-nums text-slate-900">{formatPercentage(context.par90)}</div>
            </div>
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto bg-slate-50/50 p-4 sm:p-6">
            {messages.length === 0 && (
              <div className="mx-auto flex min-h-[360px] max-w-2xl flex-col items-center justify-center text-center">
                <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-700 shadow-sm">
                  <Sparkles size={24} strokeWidth={1.5} />
                </div>
                <h3 className="text-lg font-semibold text-slate-900">Pregunta sobre la cartera activa</h3>
                <p className="mt-1 max-w-lg text-sm leading-6 text-slate-500">El agente utiliza dataset, exposición, PAR30/60/90, prioridades y drivers calculados para responder.</p>
                <div className="mt-5 grid w-full max-w-xl gap-2 sm:grid-cols-2">
                  {quickPrompts.map((prompt) => (
                    <button key={prompt} type="button" onClick={() => handleSend(prompt)} className="rounded-lg border border-slate-200 bg-white px-3 py-3 text-left text-sm text-slate-700 transition hover:border-slate-300 hover:bg-slate-50">
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((message) => (
              <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[88%] rounded-xl border px-4 py-3 text-sm leading-6 shadow-sm ${message.role === 'user' ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white text-slate-700'}`}>
                  <div className="whitespace-pre-wrap">{message.content}</div>
                  <Evidence items={message.evidence} />
                  {message.decision?.suggested_action && (
                    <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
                      <strong>Acción sugerida:</strong> {message.decision.suggested_action}
                    </div>
                  )}
                  {message.source === 'local-fallback' && (
                    <div className="mt-2 text-[10px] font-semibold uppercase tracking-wider text-amber-600">Evidence fallback · backend no disponible</div>
                  )}
                  {message.provider && message.role !== 'user' && (
                    <div className="mt-2 text-[10px] uppercase tracking-wider text-slate-400">{message.provider}</div>
                  )}
                </div>
              </div>
            ))}

            {isAnalyzing && (
              <div className="flex justify-start">
                <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500 shadow-sm">
                  <Activity size={15} className="animate-pulse" strokeWidth={1.5} />
                  Analizando evidencia…
                </div>
              </div>
            )}
          </div>

          <footer className="border-t border-slate-200 bg-white p-4 sm:p-5">
            <div className="flex items-end gap-2 rounded-xl border border-slate-200 bg-slate-50 p-2 focus-within:border-slate-400">
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={handleKeyDown}
                rows={2}
                placeholder="Pregunta por riesgo, mora, concentración o deterioro…"
                className="min-h-[48px] flex-1 resize-none border-0 bg-transparent px-2 py-2 text-sm text-slate-800 outline-none placeholder:text-slate-400"
              />
              <button type="button" aria-label="Enviar consulta" disabled={!input.trim() || isAnalyzing} onClick={() => handleSend()} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-900 text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40">
                <Send size={16} strokeWidth={1.5} />
              </button>
            </div>
            <div className="mt-2 text-[11px] text-slate-400">Enter para enviar · Shift+Enter para nueva línea</div>
          </footer>
        </section>

        <aside className="w-full shrink-0 border-t border-slate-200 bg-white lg:w-[330px] lg:border-l lg:border-t-0">
          <div className="border-b border-slate-200 px-5 py-4">
            <div className="flex items-center gap-2">
              <Database size={15} className="text-slate-500" strokeWidth={1.5} />
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Contexto activo</span>
            </div>
          </div>

          <div className="space-y-4 p-5">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <div className="text-xs text-slate-500">Dataset</div>
              <div className="mt-1 truncate text-sm font-medium text-slate-800">{context.datasetId || 'Sin dataset'}</div>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <div className="rounded-lg border border-slate-200 bg-white p-3 text-center">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">PAR30</div>
                <div className="mt-1 text-sm font-semibold tabular-nums text-slate-800">{formatPercentage(context.par30)}</div>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-3 text-center">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">PAR60</div>
                <div className="mt-1 text-sm font-semibold tabular-nums text-slate-800">{formatPercentage(context.par60)}</div>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-3 text-center">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">PAR90</div>
                <div className="mt-1 text-sm font-semibold tabular-nums text-slate-800">{formatPercentage(context.par90)}</div>
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="text-xs text-slate-500">Exposición total</div>
              <div className="mt-1 text-xl font-semibold tabular-nums text-slate-900">{formatMoney(context.exposure)}</div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="mb-2 flex items-center gap-2">
                <TrendingDown size={14} className="text-slate-500" strokeWidth={1.5} />
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Prioridades</span>
              </div>
              {context.priorities.length > 0 ? (
                <div className="space-y-0">
                  {context.priorities.slice(0, 4).map((item, index) => (
                    <div key={`${item.rank || index}-${item.title || 'priority'}`} className="border-t border-slate-100 py-2 first:border-t-0">
                      <div className="text-xs font-medium text-slate-700">#{item.rank || index + 1} {item.title || 'Prioridad'}</div>
                      <div className="mt-0.5 line-clamp-2 text-[11px] leading-4 text-slate-500">{item.why || 'Evidencia calculada disponible'}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-slate-500">No hay prioridades calculadas.</div>
              )}
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Concentración</div>
              {context.concentration.length > 0 ? (
                <div className="space-y-2">
                  {context.concentration.slice(0, 3).map((item, index) => (
                    <div key={`${item.name || 'segment'}-${index}`} className="flex items-center justify-between gap-3">
                      <span className="min-w-0 truncate text-xs text-slate-600">{item.name || item.segment || 'Segmento'}</span>
                      <span className="shrink-0 text-xs font-semibold tabular-nums text-slate-800">{formatPercentage(item.exposure_share)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-slate-500">No hay datos de concentración disponibles.</div>
              )}
            </div>

            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center gap-2 text-xs font-medium text-slate-600">
                <ShieldCheck size={14} strokeWidth={1.5} />
                Grounded analysis
              </div>
              <p className="mt-1 text-[11px] leading-4 text-slate-500">La IA interpreta evidencia calculada y mantiene revisión humana para decisiones.</p>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}
