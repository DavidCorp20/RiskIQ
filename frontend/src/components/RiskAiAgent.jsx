import { Activity, Bot, Send, Sparkles } from 'lucide-react'
import { useRiskIntelligence } from '../context/RiskIntelligenceContext'

const pct = (value) => `${(Number(value || 0) * 100).toFixed(1)}%`

function Evidence({ items }) {
  if (!Array.isArray(items) || items.length === 0) return null

  return (
    <div className="mt-3 border-t border-slate-200 pt-3">
      <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
        Evidencia calculada
      </div>
      <div className="space-y-1 text-xs leading-5 text-slate-600">
        {items.map((item, index) => (
          <div key={`evidence-${index}`}>
            {typeof item === 'string' ? item : JSON.stringify(item)}
          </div>
        ))}
      </div>
    </div>
  )
}

export default function RiskAiAgent({ onClose }) {
  const {
    context,
    input,
    setInput,
    messages,
    loading,
    send,
    onKeyDown,
    prompts,
  } = useRiskIntelligence()

  return (
    <div className="min-h-[calc(100vh-145px)] w-full overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <header className="flex items-center justify-between border-b border-slate-200 px-5 py-5 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-900 text-white">
            <Bot size={20} />
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">RISK AI AGENT</div>
            <h2 className="text-xl font-semibold tracking-tight text-slate-900">AI Risk Copilot</h2>
            <p className="text-sm text-slate-500">Respuestas fundamentadas en evidencia calculada.</p>
          </div>
        </div>
        {onClose ? (
          <button type="button" onClick={onClose} className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-600">
            Cerrar
          </button>
        ) : null}
      </header>

      <div className="grid grid-cols-3 divide-x divide-slate-200 border-b border-slate-200">
        <div className="p-4">
          <div className="text-[10px] font-semibold uppercase text-slate-400">PAR30</div>
          <div className="mt-1 text-lg font-semibold text-slate-900">{pct(context.par30)}</div>
        </div>
        <div className="p-4">
          <div className="text-[10px] font-semibold uppercase text-slate-400">PAR60</div>
          <div className="mt-1 text-lg font-semibold text-slate-900">{pct(context.par60)}</div>
        </div>
        <div className="p-4">
          <div className="text-[10px] font-semibold uppercase text-slate-400">PAR90</div>
          <div className="mt-1 text-lg font-semibold text-slate-900">{pct(context.par90)}</div>
        </div>
      </div>

      <main className="min-h-[420px] space-y-4 overflow-y-auto bg-slate-50/50 p-4 sm:p-6">
        {messages.length === 0 ? (
          <div className="mx-auto flex min-h-[360px] max-w-2xl flex-col items-center justify-center text-center">
            <Sparkles size={26} className="mb-4 text-slate-700" />
            <h3 className="text-lg font-semibold text-slate-900">Pregunta sobre la cartera activa</h3>
            <p className="mt-1 text-sm text-slate-500">
              RiskIQ utiliza exposición, PAR30/60/90, prioridades y drivers calculados.
            </p>
            <div className="mt-5 grid w-full gap-2 sm:grid-cols-2">
              {prompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => void send(prompt)}
                  className="rounded-lg border border-slate-200 bg-white p-3 text-left text-sm text-slate-700 hover:bg-slate-50"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {messages.map((message) => (
          <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[88%] rounded-xl border px-4 py-3 text-sm leading-6 shadow-sm ${message.role === 'user' ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white text-slate-700'}`}>
              <div className="whitespace-pre-wrap">{message.content}</div>
              {message.role !== 'user' ? <Evidence items={message.evidence} /> : null}
              {message.role !== 'user' ? (
                <div className="mt-2 text-[10px] uppercase tracking-wider text-slate-400">
                  {message.source}
                  {message.conversationMode ? ` · ${message.conversationMode}` : ''}
                  {message.marketContextUsed ? ' · market context' : ''}
                </div>
              ) : null}
            </div>
          </div>
        ))}

        {loading ? (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Activity size={15} className="animate-pulse" />
            Analizando evidencia…
          </div>
        ) : null}
      </main>

      <footer className="border-t border-slate-200 bg-white p-4">
        <div className="flex items-end gap-2 rounded-xl border border-slate-200 bg-white p-2">
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={onKeyDown}
            rows={2}
            placeholder="Pregunta sobre riesgo, mora, concentración o deterioro…"
            className="min-h-10 flex-1 resize-none border-0 bg-transparent px-2 py-2 text-sm text-slate-900 outline-none placeholder:text-slate-400"
          />
          <button
            type="button"
            onClick={() => void send()}
            disabled={!input.trim() || loading}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-900 text-white disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="Enviar consulta"
          >
            <Send size={16} />
          </button>
        </div>
      </footer>
    </div>
  )
}
