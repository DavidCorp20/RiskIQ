import { useCallback, useState } from 'react'
import { askCopilot } from '../api'

const EMPTY_CONTEXT = {
  datasetId: '',
  exposure: 0,
  par30: 0,
  par60: 0,
  par90: 0,
  posture: 'Sin clasificar',
  drivers: [],
  priorities: [],
  croEvidence: {},
  facts: {},
}

const normalizeNumber = (value) => (
  typeof value === 'number' && Number.isFinite(value) ? value : Number(value || 0)
)

const pct = (value) => `${(normalizeNumber(value) * 100).toFixed(2)}%`

const money = (value) => (
  `$${normalizeNumber(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
)

const firstDefined = (...values) => values.find((value) => value !== undefined && value !== null)

export function buildContext(result, datasetId = '') {
  const deterministic = result?.risk_analytics?.deterministic || result?.deterministic || {}
  const snapshot = result?.snapshot || {}
  const risk = result?.risk_intelligence || {}
  const advanced = result?.advanced_analytics || {}
  const croEvidence = result?.cro_evidence || deterministic?.cro_evidence || {}

  const par = deterministic?.par || {}
  const exposureEvidence = deterministic?.exposure
  const exposure = firstDefined(
    croEvidence?.exposure?.total_balance,
    exposureEvidence,
    snapshot?.outstanding_balance,
    risk?.materiality?.exposure,
    result?.exposure,
    0,
  )

  const readPar = (key) => normalizeNumber(firstDefined(
    croEvidence?.par?.[key]?.ratio,
    par?.[key]?.ratio,
    snapshot?.[key],
    0,
  ))

  return {
    datasetId: datasetId || result?.dataset_id || '',
    exposure: normalizeNumber(exposure),
    par30: readPar('par30'),
    par60: readPar('par60'),
    par90: readPar('par90'),
    posture: risk?.posture?.label || risk?.posture?.level || result?.severity || 'Sin clasificar',
    drivers: Array.isArray(result?.drivers)
      ? result.drivers
      : Array.isArray(result?.deterioration_drivers)
        ? result.deterioration_drivers
        : Array.isArray(deterministic?.drivers)
          ? deterministic.drivers
          : Array.isArray(advanced?.deterioration_drivers)
            ? advanced.deterioration_drivers
            : [],
    priorities: Array.isArray(result?.decisions)
      ? result.decisions
      : Array.isArray(risk?.priorities)
        ? risk.priorities
        : [],
    croEvidence: croEvidence && typeof croEvidence === 'object' ? croEvidence : {},
    facts: deterministic?.facts || result?.facts || {},
  }
}

export function buildRiskFacts(context) {
  return {
    dataset_id: context.datasetId,
    facts: context.facts,
    cro_evidence: context.croEvidence,
    summary: { status: context.posture },
  }
}

export function localAnswer(question, context) {
  const q = String(question || '').trim().toLowerCase()
  const evidence = context.croEvidence || {}
  const par = evidence.par || {}

  if (/^hola$|^holi$|^hello$|^buenas(?:\s+(dias|tardes|noches))?$/.test(q)) {
    return 'Hola. Soy el copiloto de RiskIQ. ¿Qué quieres revisar o hacer?'
  }

  if (/par\s*30|mora\s*30/.test(q) && par.par30?.ratio !== undefined) {
    return `El PAR30 calculado es ${pct(par.par30.ratio)}${par.par30.balance !== undefined ? `, equivalente a ${money(par.par30.balance)} de exposición` : ''}.`
  }

  if (/par\s*60|mora\s*60/.test(q) && par.par60?.ratio !== undefined) {
    return `El PAR60 calculado es ${pct(par.par60.ratio)}${par.par60.balance !== undefined ? `, equivalente a ${money(par.par60.balance)} de exposición` : ''}.`
  }

  if (/par\s*90|mora\s*90/.test(q) && par.par90?.ratio !== undefined) {
    return `El PAR90 calculado es ${pct(par.par90.ratio)}${par.par90.balance !== undefined ? `, equivalente a ${money(par.par90.balance)} de exposición` : ''}.`
  }

  if (/expos|saldo|balance|capital/.test(q) && evidence.exposure?.total_balance !== undefined) {
    return `La exposición total calculada es ${money(evidence.exposure.total_balance)}.`
  }

  return 'No pude consultar el Copilot en este momento. La evidencia local sigue disponible; vuelve a intentar la consulta para obtener la interpretación completa.'
}

export default function useRiskCopilot({ result, datasetId = '' } = {}) {
  const context = buildContext(result, datasetId)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)

  const send = useCallback(async (questionValue = '') => {
    const question = String(questionValue || input).trim()
    if (!question || loading) return

    const userMessage = {
      id: `${Date.now()}-u`,
      role: 'user',
      content: question,
    }

    const nextConversation = [...messages, userMessage]
    setMessages(nextConversation)
    setInput('')
    setLoading(true)

    try {
      if (!context.datasetId) {
        throw new Error('No hay una cartera activa para consultar.')
      }

      const response = await askCopilot({
        question,
        dataset_id: context.datasetId,
        risk_facts: buildRiskFacts(context),
        drivers: context.drivers,
        decisions: context.priorities,
        conversation: nextConversation.map(({ role, content }) => ({ role, content })),
      })

      setMessages((current) => [
        ...current,
        {
          id: `${Date.now()}-a`,
          role: 'agent',
          content: response?.answer || 'El backend no devolvió una respuesta interpretable.',
          evidence: response?.evidence || [],
          source: response?.provider || response?.mode || 'RiskIQ AI',
          marketContext: response?.market_context || null,
          marketContextUsed: Boolean(response?.market_context_used),
          conversationMode: response?.conversation_mode || null,
        },
      ])
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: `${Date.now()}-f`,
          role: 'agent',
          content: localAnswer(question, context),
          evidence: [],
          source: error?.message || 'RiskIQ Evidence Fallback',
        },
      ])
    } finally {
      setLoading(false)
    }
  }, [context, input, loading, messages])

  const onKeyDown = useCallback((event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void send()
    }
  }, [send])

  return {
    context,
    input,
    setInput,
    messages,
    loading,
    send,
    onKeyDown,
    prompts: [
      '¿Qué debería revisar primero?',
      '¿Dónde está concentrado el riesgo?',
      '¿Qué está deteriorando la cartera?',
      'Explícame el PAR30',
    ],
  }
}
