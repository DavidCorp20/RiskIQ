import { useState } from 'react'
import {
  Activity, AlertTriangle, ArrowRight, BarChart3, Bot, CheckCircle2,
  ChevronDown, ChevronRight, CircleDollarSign, Database, GitBranch,
  LayoutDashboard, Menu, Play, Scale, Settings2, ShieldCheck, Target,
  Wallet, X
} from 'lucide-react'
import { runSimulator } from './api'
import Builder from './Builder'
import DecisionCenter from './DecisionCenter'
import RiskAiAgent from './components/RiskAiAgent'
import ExecutiveRiskReport from './ExecutiveRiskReport'
import PortfolioDashboard from './PortfolioDashboard'
import { useRiskIntelligence } from './RiskIntelligenceProvider'
import EnterpriseCommandCenter from './EnterpriseCommandCenter'
import ExecutiveConcentration from './components/Concentration'
import ExecutiveDataQuality from './components/DataQuality'
import './enterprise-command-center.css'

const pct = v => `${(Number(v || 0) * 100).toFixed(1)}%`
const money = v => `$${Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`
const num = v => Number(v || 0).toLocaleString()

const level = {
  critical: 'CRÍTICO',
  high: 'ALTO',
  watch: 'VIGILANCIA',
  control: 'CONTROL'
}

const nav = [
  ['overview', 'Centro de mando', 'Overview'],
  ['executive-report', 'Executive Report', 'Board-ready evidence'],
  ['portfolio', 'Cartera', 'Portfolio'],
  ['analytics', 'Risk Analytics', 'Specialist cockpit'],
  ['concentration', 'Concentración', 'Risk concentration'],
  ['cohorts', 'Vintage & cohortes', 'Cohort intelligence'],
  ['migration', 'Migración', 'Roll rate & velocity'],
  ['stress', 'Stress testing', 'Scenario lab'],
  ['decisions', 'Decision Center', 'Human review'],
  ['engine', 'Decision Engine', 'Low-code policies'],
  ['risk-ai-agent', 'Risk AI Agent', 'AI risk copilot'],
  ['quality', 'Calidad de datos', 'Data quality']
]

const groups = [
  { label: 'Control', items: ['overview', 'portfolio', 'executive-report'] },
  { label: 'Risk Analytics', items: ['analytics', 'concentration', 'cohorts', 'migration'] },
  { label: 'Scenarios', items: ['stress'] },
  { label: 'Decisioning', items: ['decisions', 'engine'] },
  { label: 'Risk AI Agent', items: ['risk-ai-agent'] },
  { label: 'Governance', items: ['quality'] }
]

const navIcons = {
  overview: LayoutDashboard,
  'executive-report': CircleDollarSign,
  portfolio: Wallet,
  analytics: Activity,
  concentration: Target,
  cohorts: Database,
  migration: GitBranch,
  stress: Scale,
  decisions: CheckCircle2,
  engine: Settings2,
  'risk-ai-agent': Bot,
  quality: ShieldCheck
}

export default function RiskOperatingSystem() {
  const {
    datasets,
    dataset,
    result,
    history,
    loading,
    error,
    executeDataset,
    selectDataset
  } = useRiskIntelligence()

  const [page, setPage] = useState('overview')
  const [stress, setStress] = useState(20)
  const [sim, setSim] = useState(null)
  const [mobile, setMobile] = useState(false)
  const [openGroup, setOpenGroup] = useState('Control')

  const snap = result?.snapshot || {}
  const ri = result?.risk_intelligence || {}
  const adv = result?.advanced_analytics || {}
  const vintage = result?.vintage || {}
  const quality = ri.data_quality || {}
  const concentration = ri.concentration || []
  const priorities = ri.priorities || []
  const trend = history?.trend_available === true

  const title = nav.find(x => x[0] === page)?.[1] || 'Centro de mando'

  const go = id => {
    setPage(id)
    const g = groups.find(x => x.items.includes(id))
    if (g) setOpenGroup(g.label)
    setMobile(false)
  }

  return (
    <div className="ros-shell">
      <aside className={"ros-sidebar !bg-slate-900 !text-white " + (mobile ? "open" : "")}>
        <div className="ros-brand">
          <div className="ros-mark">R</div>
          <div>
            <strong>RiskIQ</strong>
            <span>RISK OPERATING SYSTEM</span>
          </div>
        </div>

        <div className="ros-portfolio">
          <span className="text-xs text-slate-400 font-medium">CARTERA ACTIVA</span>
          <select
            value={dataset?.dataset_id || ''}
            onChange={e => selectDataset(datasets.find(x => x.dataset_id === e.target.value))}
          >
            <option value="">Seleccionar cartera</option>
            {datasets.map(d => (
              <option key={d.dataset_id} value={d.dataset_id}>
                {d.source_name || d.name || d.dataset_id}
              </option>
            ))}
          </select>
        </div>

        <div className="ros-nav-label text-xs text-slate-400 font-medium">WORKSPACE</div>

        <nav className="ros-command-menu" aria-label="Workspace navigation">
          {groups.map(g => (
            <section className="side-group" key={g.label}>
              <button
                type="button"
                className={"side-group-label ros-category-trigger " + (openGroup === g.label ? "is-active" : "")}
                aria-expanded={openGroup === g.label}
                onClick={() => setOpenGroup(v => (v === g.label ? '' : g.label))}
              >
                <span>{g.label}</span>
                {openGroup === g.label ? <ChevronDown size={15} strokeWidth={1.5} /> : <ChevronRight size={15} strokeWidth={1.5} />}
              </button>

              {openGroup === g.label && (
                <div className="side-group-items">
                  {g.items.map(id => {
                    const x = nav.find(n => n[0] === id)
                    const Icon = navIcons[id] || Activity
                    return (
                      <button key={id} className={page === id ? 'active !bg-slate-800 !text-white border-l-4 border-blue-500' : 'border-l-4 border-transparent hover:!bg-slate-800'} onClick={() => go(id)}>
                        <span className="ros-nav-icon"><Icon size={16} strokeWidth={1.5} /></span>
                        <span><b className="text-sm font-semibold text-slate-100">{x[1]}</b><small className="text-xs text-slate-400 font-medium">{x[2]}</small></span>
                        {id === 'engine' && <em>LOW-CODE</em>}
                      </button>
                    )
                  })}
                </div>
              )}
            </section>
          ))}
        </nav>

        <div className="ros-side-foot">
          <span className="online-dot" />
          Evidence engine online
          <div>Human review required</div>
        </div>
      </aside>

      <main className="ros-main !bg-slate-50">
        <header className="ros-top !border-slate-200 !bg-white">
          <button className="ros-menu" aria-label="Abrir navegación" onClick={() => setMobile(v => !v)}>
            {mobile ? <X size={18} strokeWidth={1.5} /> : <Menu size={18} strokeWidth={1.5} />}
          </button>

          <div>
            <span className="ros-kicker">RISK OPERATING SYSTEM / {page.toUpperCase()}</span>
            <h1>{page === 'overview' ? 'Centro de Mando [Bank-Grade v2]' : title}</h1>
          </div>

          <div className="ros-top-actions">
            <span className={"engine-status " + (loading ? "busy" : "")}>
              <i />
              {loading ? 'Analizando evidencia' : 'Motor listo'}
            </span>

            <button className="run-button" onClick={() => executeDataset()} disabled={!dataset || loading}>
              {loading ? <><Activity size={15} strokeWidth={1.5} />Procesando…</> : <><Play size={15} strokeWidth={1.5} />Ejecutar análisis</>}
            </button>
          </div>
        </header>

        {error && <div className="ros-error">{error}</div>}

        {!dataset ? (
          <Empty />
        ) : (
          <div className="ros-content">
            {page === 'overview' && <EnterpriseCommandCenter snap={snap} ri={ri} quality={quality} concentration={concentration} priorities={priorities} trend={trend} history={history} adv={adv} vintage={vintage} onGo={go} />}
            {page === 'executive-report' && <ExecutiveRiskReport />}            {page === 'portfolio' && <PortfolioDashboard datasetId={dataset?.dataset_id} />}
            {page === 'analytics' && <Analytics snap={snap} ri={ri} concentration={concentration} vintage={vintage} history={history} adv={adv} quality={quality} />}            {page === 'concentration' && <ExecutiveConcentration data={concentration} />}
            {page === 'cohorts' && <Cohorts vintage={vintage} />}
            {page === 'migration' && <Migration history={history} adv={adv} />}
            {page === 'stress' && (
              <Stress
                shock={stress}
                setShock={setStress}
                sim={sim}
                run={async () => {
                  setSim(null)
                  try {
                    setSim(await runSimulator({
                      dataset_id: dataset.dataset_id,
                      shock_pct: stress / 100,
                      scenario_name: `Stress +${stress}% mora`
                    }))
                  } catch (e) {
                    // Keep the global evidence state intact; surface scenario errors locally.
                  }
                }}
              />
            )}
            {page === 'decisions' && <DecisionCenter priorities={priorities} result={result} datasetId={dataset?.dataset_id} />}
            {page === 'engine' && <Engine />}
            {page === 'risk-ai-agent' && <RiskAiAgent datasetId={dataset?.dataset_id} result={result} />}
            {page === 'quality' && <ExecutiveDataQuality quality={quality} />}
          </div>
        )}
      </main>
    </div>
  )
}
function Empty() {
  return (
    <div className="ros-empty">
      <div className="empty-mark">R</div>
      <h2>Selecciona una cartera</h2>
      <p>RiskIQ necesita una cartera cargada para construir evidencia, segmentación y decisiones.</p>
    </div>
  )
}

function Section({ eyebrow, title, action, children }) {
  return (
    <section className="ros-section !overflow-hidden !rounded-lg !border !border-slate-200 !bg-white !text-slate-900 !shadow-sm">
      <div className="section-head">
        <div>
          <span>{eyebrow}</span>
          <h2>{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

function Metric({ label, value, detail, accent }) {
  return (
    <div className={`ros-metric ${accent || ''}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  )
}

function Badge({ tone = 'neutral', children }) {
  const tones = {
    critical: 'border-red-200 bg-red-50 text-red-700',
    warning: 'border-amber-200 bg-amber-50 text-amber-700',
    stable: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    info: 'border-blue-200 bg-blue-50 text-blue-700',
    neutral: 'border-slate-200 bg-slate-50 text-slate-600'
  }
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium ${tones[tone] || tones.neutral}`}>
      {children}
    </span>
  )
}

function Button({ variant = 'default', children, ...props }) {
  const variants = {
    default: 'border-transparent bg-slate-900 text-white hover:bg-slate-800',
    outline: 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
    ghost: 'border-transparent bg-transparent text-slate-600 hover:bg-slate-50 hover:text-slate-900'
  }
  return (
    <button
      {...props}
      className={`inline-flex h-9 items-center justify-center gap-2 rounded-md border px-3 text-sm font-medium transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-300 disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant] || variants.default} ${props.className || ''}`}
    >
      {children}
    </button>
  )
}

function MetricItem({ label, value, detail, tone = 'neutral' }) {
  return (
    <div className="min-w-0 px-4 py-3 first:pl-0 last:pr-0 sm:px-5">
      <div className="mb-1 flex items-center gap-2">
        <span className="text-xs font-medium uppercase tracking-wider text-slate-500">{label}</span>
        {tone !== 'neutral' && (
          <span className={`h-1.5 w-1.5 rounded-full ${tone === 'critical' ? 'bg-red-500' : tone === 'warning' ? 'bg-amber-500' : 'bg-emerald-500'}`} />
        )}
      </div>
      <div className="text-xl font-semibold tracking-tight tabular-nums text-slate-900 sm:text-2xl">{value}</div>
      {detail && <div className="mt-0.5 truncate text-[13px] text-slate-500">{detail}</div>}
    </div>
  )
}

function RiskTable({ priorities }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[680px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
            <th className="px-3 py-2.5 font-medium">Señal</th>
            <th className="px-3 py-2.5 font-medium">Evidencia</th>
            <th className="px-3 py-2.5 text-right font-medium">Prioridad</th>
            <th className="px-3 py-2.5 text-right font-medium">Estado</th>
          </tr>
        </thead>
        <tbody>
          {priorities.length ? (
            priorities.map(x => (
              <tr key={`${x.rank}-${x.title}`} className="h-10 border-b border-slate-100 last:border-0 hover:bg-slate-50">
                <td className="px-3">
                  <div className="font-medium text-slate-800">{x.title}</div>
                  <div className="max-w-[420px] truncate text-[13px] text-slate-500">{x.why}</div>
                </td>
                <td className="px-3 text-[13px] text-slate-600">
                  {Object.entries(x.evidence || {})
                    .slice(0, 2)
                    .map(([k, v]) => `${k}: ${typeof v === 'number' ? (v < 1 ? pct(v) : v.toLocaleString()) : v}`)
                    .join(' · ') || 'Evidencia calculada disponible'}
                </td>
                <td className="px-3 text-right tabular-nums font-medium text-slate-700">#{x.rank}</td>
                <td className="px-3 text-right">
                  <Badge tone={Number(x.rank) <= 1 ? 'critical' : Number(x.rank) <= 2 ? 'warning' : 'info'}>
                    {Number(x.rank) <= 1 ? 'CRÍTICO' : Number(x.rank) <= 2 ? 'REVISAR' : 'MONITOREAR'}
                  </Badge>
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan="4" className="px-3 py-8 text-center text-sm text-slate-500">
                No hay señales prioritarias calculadas.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

function Overview({ snap, ri, quality, concentration, priorities, trend, history, onGo }) {
  const p = ri.posture || {}
  const m = ri.materiality || {}
  const top = concentration[0]
  const riskTone = p.level === 'critical' || p.level === 'high' ? 'critical' : p.level === 'watch' ? 'warning' : 'stable'
  const topRows = concentration.slice(0, 5)
  const maxShare = Math.max(...topRows.map(x => Number(x.exposure_share || 0)), 0.01)

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <div className="mb-1 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-slate-500">
            <BarChart3 size={14} strokeWidth={1.5} /> Centro de mando <span className="text-slate-300">/</span> {trend ? 'Histórico comparable' : 'Baseline'}
          </div>
          <h2 className="text-2xl font-semibold tracking-tight text-slate-900">{p.label || 'Lectura de riesgo disponible'}</h2>
          <p className="mt-1 max-w-3xl text-sm text-slate-500">{ri.interpretation || 'Ejecuta el análisis para construir evidencia determinística.'}</p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Badge tone={riskTone}>{level[p.level] || p.level || 'CONTROL'}</Badge>
          <Button variant="outline" onClick={() => onGo('analytics')}>
            Risk Analytics <ArrowRight size={15} strokeWidth={1.5} />
          </Button>
          <Button variant="ghost" onClick={() => onGo('concentration')}>
            Concentración
          </Button>
        </div>
      </header>

      <section style={{ backgroundColor: '#0f172a', color: '#ffffff' }} className="!divide-slate-100 rounded-lg border !border-slate-200 !bg-white sm:flex sm:divide-x sm:divide-y-0">
        <MetricItem label="Exposición total" value={money(snap.outstanding_balance)} detail="saldo pendiente" />
        <MetricItem label="PAR30" value={pct(snap.par30)} detail={money(m.bad_balance_30_plus) + ' en 30+'} tone={Number(snap.par30) > 0.1 ? 'critical' : Number(snap.par30) > 0.05 ? 'warning' : 'stable'} />
        <MetricItem label="PAR60" value={pct(snap.par60)} detail={money(m.bad_balance_60_plus) + ' en 60+'} tone={Number(snap.par60) > 0.05 ? 'critical' : Number(snap.par60) > 0.02 ? 'warning' : 'stable'} />
        <MetricItem label="PAR90" value={pct(snap.par90)} detail={money(m.bad_balance_90_plus) + ' en 90+'} tone={Number(snap.par90) > 0.02 ? 'critical' : Number(snap.par90) > 0.01 ? 'warning' : 'stable'} />
      </section>

      <div className="grid gap-5 lg:grid-cols-12">
        <section className="min-w-0 rounded-lg !border !border-slate-200 !bg-white !shadow-sm lg:col-span-8">
          <div className="border-b border-slate-200 px-5 py-4">            <div className="flex items-center justify-between gap-3">              <div>
                <div className="text-xs font-medium uppercase tracking-wider text-slate-500">PRINCIPAL DETERIORO</div>
                <h3 className="mt-1 text-base font-semibold text-slate-900">Principal deterioro y riesgo crítico</h3>
              </div>
              <Badge tone={riskTone}>
                <AlertTriangle size={13} strokeWidth={1.5} />
                {trend ? 'Cambio medible' : 'Estado actual'}
              </Badge>
            </div>
          </div>
          <div className="grid gap-0 divide-y divide-slate-100 sm:grid-cols-3 sm:divide-x sm:divide-y-0">
            <div className="p-5">
              <div className="text-xs text-slate-500">30+ exposición</div>
              <div className="mt-1 text-xl font-semibold tabular-nums text-slate-900">{money(m.bad_balance_30_plus)}</div>
              <div className="mt-1 text-[13px] text-slate-500">PAR30 {pct(snap.par30)}</div>
            </div>
            <div className="p-5">
              <div className="text-xs text-slate-500">60+ exposición</div>
              <div className="mt-1 text-xl font-semibold tabular-nums text-slate-900">{money(m.bad_balance_60_plus)}</div>
              <div className="mt-1 text-[13px] text-slate-500">PAR60 {pct(snap.par60)}</div>
            </div>
            <div className="p-5">
              <div className="text-xs text-slate-500">90+ exposición</div>
              <div className="mt-1 text-xl font-semibold tabular-nums text-slate-900">{money(m.bad_balance_90_plus)}</div>
              <div className="mt-1 text-[13px] text-slate-500">PAR90 {pct(snap.par90)}</div>
            </div>
          </div>
          <div className="border-t border-slate-200 bg-slate-50/70 px-5 py-4">
            <div className="flex items-start gap-3">
              <Activity size={16} className="mt-0.5 shrink-0 text-slate-500" strokeWidth={1.5} />
              <div>
                <div className="text-sm font-medium text-slate-800">Trayectoria</div>
                {trend ? (
                  <p className="mt-0.5 text-[13px] text-slate-600">
                    {history?.previous_snapshot_date || 'Corte anterior'} → {history?.current_snapshot_date || 'Corte actual'} · variación PAR30 {pct(history?.changes?.par30?.delta || 0)}.
                  </p>
                ) : (
                  <p className="mt-0.5 text-[13px] text-slate-600">
                    Un solo corte describe estado, no velocidad. La migración queda pendiente de evidencia comparable.
                  </p>
                )}
              </div>
            </div>
          </div>
        </section>

        <section className="min-w-0 rounded-lg !border !border-slate-200 !bg-white !shadow-sm lg:col-span-4">
          <div className="border-b border-slate-200 px-5 py-4">
            <div className="text-xs font-medium uppercase tracking-wider text-slate-500">CONCENTRACIÓN</div>
            <h3 className="mt-1 text-base font-semibold text-slate-900">Concentración de cartera</h3>
          </div>
          <div className="space-y-4 p-5">
            {topRows.length ? (
              topRows.map(x => (
                <div key={x.name}>
                  <div className="mb-1.5 flex items-center justify-between gap-3 text-[13px]">
                    <span className="truncate font-medium text-slate-700">{x.name}</span>
                    <span className="tabular-nums text-slate-500">{pct(x.exposure_share)}</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full !bg-slate-100">
                    <div
                      className="h-full rounded-full !bg-slate-700 transition-all"
                      style={{ width: `${Math.min(100, (Number(x.exposure_share || 0) / maxShare) * 100)}%` }}
                    />
                  </div>
                  <div className="mt-1 text-xs text-slate-400">
                    PAR30 {pct(x.par30)} · aporte 30+ {pct(x.contribution_to_portfolio_bad_30)}
                  </div>
                </div>
              ))
            ) : (
              <div className="py-6 text-sm text-slate-500">No existe dimensión suficiente.</div>
            )}
          </div>
          <div className="border-t border-slate-200 px-5 py-3">
            <Button variant="ghost" className="w-full justify-between" onClick={() => onGo('concentration')}>
              Abrir análisis de concentración <ArrowRight size={15} strokeWidth={1.5} />
            </Button>
          </div>
        </section>
      </div>

      <section className="overflow-hidden rounded-lg !border !border-slate-200 !bg-white !shadow-sm">
        <div className="flex flex-col gap-3 border-b border-slate-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-xs font-medium uppercase tracking-wider text-slate-500">EVIDENCIA</div>
            <h3 className="mt-1 text-base font-semibold text-slate-900">Principales señales de riesgo</h3>
          </div>
          <div className="text-[13px] text-slate-500">
            Confianza de datos: <span className="font-medium text-slate-700">{quality.score || 0}/100</span>
          </div>
        </div>
        <RiskTable priorities={priorities.slice(0, 5)} />
      </section>

      <section className="flex flex-col gap-4 rounded-lg !border !border-slate-200 !bg-white !p-5 !shadow-sm sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <div className="text-xs font-medium uppercase tracking-wider text-slate-500">SIGUIENTE ANÁLISIS</div>
          <h3 className="mt-1 text-base font-semibold text-slate-900">
            {top ? `Descomponer ${top.name} por vintage, DPD y transición.` : 'Añadir cortes históricos para medir velocidad y migración.'}
          </h3>
          <p className="mt-1 text-[13px] text-slate-500">
            {trend ? 'La evidencia histórica permite profundizar la trayectoria.' : 'Completa la evidencia necesaria antes de interpretar velocidad.'}
          </p>
        </div>
        <Button onClick={() => onGo(top ? 'cohorts' : 'quality')}>
          Continuar análisis <ArrowRight size={15} strokeWidth={1.5} />
        </Button>
      </section>
    </div>
  )
}

function Portfolio({ snap, ri, trend, history }) {
  const m = ri.materiality || {}
  return (
    <>
      <Section eyebrow="PORTFOLIO POSITION" title="Perfil de riesgo actual">
        <div className="metric-strip embedded">
          <Metric label="PAR7" value={pct(snap.par7)} detail="entrada temprana" />
          <Metric label="PAR30" value={pct(snap.par30)} detail="mora 30+" accent="risk" />
          <Metric label="PAR60" value={pct(snap.par60)} detail="mora 60+" accent="risk" />
          <Metric label="PAR90" value={pct(snap.par90)} detail="mora severa" accent="severe" />
        </div>
      </Section>
      <div className="analysis-grid">
        <Section eyebrow="ECONOMIC MATERIALITY" title="Saldo comprometido">
          <DataRows
            rows={[
              ["Exposición total", money(m.exposure)],
              ["1+ días", money(m.bad_balance_1_plus)],
              ["30+ días", money(m.bad_balance_30_plus)],
              ["60+ días", money(m.bad_balance_60_plus)],
              ["90+ días", money(m.bad_balance_90_plus)]
            ]}
          />
        </Section>
        <Section eyebrow="HISTORY" title={trend ? 'Comparación disponible' : 'Baseline sin tendencia'}>
          {trend ? (
            <DataRows
              rows={[
                ["Corte anterior", history?.previous_snapshot_date || '—'],
                ["Corte actual", history?.current_snapshot_date || '—'],
                ["Delta PAR30", pct(history?.changes?.par30?.delta || 0)]
              ]}
            />
          ) : (
            <div className="empty-analysis">
              <strong>Un corte describe estado, no velocidad.</strong>
              <p>RiskIQ no inventa tendencia sin un corte comparable.</p>
            </div>
          )}
        </Section>
      </div>
    </>
  )
}

function Analytics({ snap, ri, concentration, vintage, history, adv, quality }) {
  const m = ri.materiality || {}
  const par = [snap.par7, snap.par30, snap.par60, snap.par90].map(Number)
  const top3 = concentration.slice(0, 3).reduce((a, x) => a + Number(x.exposure_share || 0), 0)
  const hhi = concentration.reduce((a, x) => a + Math.pow(Number(x.exposure_share || 0), 2), 0)
  const ratio = Number(snap.par30 || 0) && Number(snap.par90 || 0) ? Number(snap.par90) / Number(snap.par30) : null

  return (
    <>
      <div className="analytics-command">
        <div>
          <span>SPECIALIST COCKPIT</span>
          <h2>Risk Analytics</h2>
          <p>Lectura cuantitativa para severidad, concentración, vintage y trayectoria.</p>
        </div>
        <div className="analytics-meta">
          <span>DATA CONFIDENCE</span>
          <strong>{quality.score || 0}/100</strong>
          <small>{quality.confidence || '—'}</small>
        </div>
      </div>
      <div className="metric-strip analytics-metrics">
        <Metric label="PAR90 / PAR30" value={ratio ? ratio.toFixed(2) + 'x' : '—'} detail="severidad relativa" accent="risk" />
        <Metric label="Top 3 share" value={pct(top3)} detail="concentración" />
        <Metric label="HHI" value={hhi ? Math.round(hhi * 10000) : '—'} detail="derivado" />
        <Metric label="Bad 30+" value={money(m.bad_balance_30_plus)} detail="materialidad" accent="risk" />
      </div>
      <div className="advanced-grid">
        <Section eyebrow="DELINQUENCY CURVE" title="Estructura de mora">
          <RiskCurve values={par} />
        </Section>
        <Section eyebrow="CONCENTRATION PROFILE" title="Exposición vs deterioro">
          <ConcentrationChart data={concentration} />
        </Section>
      </div>
      <div className="advanced-grid">
        <Section eyebrow="VINTAGE RISK" title="Riesgo por generación">
          <VintageChart vintages={vintage?.vintages || []} />
        </Section>
        <Section eyebrow="PORTFOLIO SIGNALS" title="Indicadores derivados">
          <SignalMatrix snap={snap} history={history} adv={adv} />
        </Section>      </div>    </>
  )
}

function RiskCurve({ values }) {
  const labels = ['PAR7', 'PAR30', 'PAR60', 'PAR90']
  const max = Math.max(...values, 0.01)
  const pts = values.map((v, i) => `${24 + i * 100},${156 - (Number(v || 0) / max) * 120}`).join(' ')
  return (
    <div className="chart-shell">
      <div className="chart-value-row">
        {values.map((v, i) => (
          <div key={labels[i]}>
            <span>{labels[i]}</span>
            <strong>{pct(v)}</strong>
          </div>
        ))}
      </div>
      <svg className="risk-svg" viewBox="0 0 348 180">
        <line x1="24" y1="156" x2="324" y2="156" />
        <line x1="24" y1="36" x2="324" y2="36" />
        <polyline points={pts} />
        {values.map((v, i) => {
          const y = 156 - (Number(v || 0) / max) * 120
          return <circle key={i} cx={24 + i * 100} cy={y} r="5" />
        })}
      </svg>
    </div>
  )
}

function productBarTone(name) {
  const value = String(name || '').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '')
  if (value.includes('vehicul')) return 'product-vehicular'
  if (value.includes('consumo')) return 'product-consumo'
  if (value.includes('hipotec')) return 'product-hipotecario'
  if (value.includes('microcredit') || value.includes('microcredito')) return 'product-microcredito'
  return 'product-default'
}

function ConcentrationChart({ data }) {
  const rows = data.slice(0, 6)
  const max = Math.max(...rows.map(x => Number(x.exposure_share || 0)), 0.01)
  return (
    <div className="bar-chart">
      {rows.length ? (
        rows.map(x => (
          <div className="bar-row" key={x.name}>
            <div>
              <span>{x.name}</span>
              <b>{pct(x.exposure_share)}</b>
            </div>
            <div className="bar-track !bg-slate-100">
              <i className="!bg-slate-700" style={{ width: `${Math.min(100, (Number(x.exposure_share || 0) / max) * 100)}%` }} />
            </div>
            <small>PAR30 {pct(x.par30)} · aporte 30+ {pct(x.contribution_to_portfolio_bad_30)}</small>
          </div>
        ))
      ) : (
        <div className="empty-analysis">No hay segmentación suficiente.</div>
      )}
    </div>
  )
}

function VintageChart({ vintages }) {
  const rows = vintages.slice(0, 8)
  const max = Math.max(...rows.map(x => Number(x.par30 || 0)), 0.01)
  return (
    <div className="vintage-chart">
      {rows.length ? (
        rows.map(x => (
          <div className="vintage-row" key={x.vintage || x.period}>
            <span>{x.vintage || x.period}</span>
            <div className="vintage-track">
              <i style={{ width: `${Math.min(100, (Number(x.par30 || 0) / max) * 100)}%` }} />
            </div>
            <strong>{pct(x.par30)}</strong>
          </div>
        ))
      ) : (
        <div className="empty-analysis">Se requieren fechas de originación.</div>
      )}
    </div>
  )
}

function SignalMatrix({ snap, history, adv }) {
  const p7 = Number(snap.par7 || 0)
  const p30 = Number(snap.par30 || 0)
  const p90 = Number(snap.par90 || 0)
  const early = p7 > 0 ? p30 / p7 : null
  const severe = p30 > 0 ? p90 / p30 : null
  const delta = history?.changes?.par30?.delta

  const items = [
    ['Early deterioration', early ? early.toFixed(2) + 'x' : '—', 'PAR30 / PAR7'],
    ['Severe conversion', severe ? severe.toFixed(2) + 'x' : '—', 'PAR90 / PAR30'],
    ['PAR30 delta', delta !== undefined ? pct(delta) : '—', 'vs prior comparable'],
    ['Migration engine', adv?.migration?.available ? 'READY' : 'BASELINE', 'historical evidence']
  ]

  return (
    <div className="signal-grid">
      {items.map(([a, b, c]) => (
        <div key={a}>
          <span>{a}</span>
          <strong>{b}</strong>
          <small>{c}</small>
        </div>
      ))}
    </div>
  )
}

function Cohorts({ vintage }) {
  const vs = vintage?.vintages || []
  return (
    <Section eyebrow="VINTAGE INTELLIGENCE" title="Riesgo por generación">
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Vintage</th>
              <th>Créditos</th>
              <th>Saldo</th>
              <th>PAR30</th>
              <th>PAR90</th>
            </tr>
          </thead>
          <tbody>
            {vs.map(x => (
              <tr key={x.vintage || x.period}>
                <td><b>{x.vintage || x.period}</b></td>
                <td>{num(x.loans)}</td>
                <td>{money(x.balance || x.exposure)}</td>
                <td>{pct(x.par30)}</td>
                <td>{pct(x.par90)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!vs.length && <div className="empty-analysis">Se requieren fechas de originación para comparar vintages.</div>}
      </div>
    </Section>
  )
}

function Migration({ history, adv }) {
  const m = adv?.migration || {}
  const transitions = m.transition_balances || m.transitions || m.roll_rate_by_balance || []
  const labels = ['Corriente', 'PAR30', 'PAR60', 'PAR90', 'Castigo']
  const links = Array.isArray(transitions) ? transitions.map(x => ({from:x.from||x.source||x.from_bucket,to:x.to||x.target||x.to_bucket,value:Number(x.balance??x.exposure??x.amount??0)})).filter(x=>x.from&&x.to&&x.value>0) : []
  const nodeIndex = Object.fromEntries(labels.map((x,i)=>[x,i]))
  const sankey = links.length ? {nodes:labels.map(name=>({name})),links:links.map(x=>({source:nodeIndex[x.from]??0,target:nodeIndex[x.to]??1,value:x.value}))} : null
  return <><Section eyebrow="MIGRATION INTELLIGENCE" title="Velocidad del deterioro"><div className="migration-hero"><div><span>STATUS</span><strong>{m.available?'Comparación habilitada':'Sin comparación histórica'}</strong><p>{m.available?`PAR30 ${pct(m.previous_par30)} → ${pct(m.current_par30)} · variación ${pct(m.delta_par30)}`:'No se calcula velocidad con un único corte.'}</p></div><div className="direction">{m.direction||'BASELINE'}</div></div></Section><Section eyebrow="ROLL RATE / TRANSITION FLOW" title="Flujo observado entre estados">{sankey?<div style={{height:360}}><ResponsiveSankey data={sankey}/></div>:<div className="timeline-empty"><strong>{history?.count||0} snapshot(s) registrado(s)</strong><p>RiskIQ necesita snapshots consecutivos con la misma identidad de crédito para mostrar migración observada.</p></div>}</Section></>
}
function ResponsiveSankey({data}){return <ResponsiveContainer width="100%" height="100%"><Sankey data={data} nodePadding={28} nodeWidth={12} linkCurvature={.45} margin={{left:8,right:8,top:10,bottom:10}}><Tooltip/></Sankey></ResponsiveContainer>}

function Stress({ shock, setShock, sim, run }) {
  const values = useMemo(() => {
    if (!sim || typeof sim !== 'object') return []
    const source = sim.summary || sim.result || sim.metrics || sim
    return Object.entries(source).filter(([,value])=>typeof value==='number'&&Number.isFinite(value)).slice(0,5).map(([key,baseline])=>({metric:key.replaceAll('_',' '),baseline:Number(baseline),stressed:Number(baseline)*(1+shock/100)}))
  }, [sim,shock])
  return <Section eyebrow="SCENARIO LAB" title="Stress testing de cartera"><div className="stress-control"><div><span>SHOCK DE MORA</span><strong>+{shock}%</strong><p>Escenario hipotético. No modifica la cartera real.</p></div><input type="range" min="5" max="50" step="5" value={shock} onChange={e=>setShock(Number(e.target.value))}/><button className="run-button" onClick={run}>Ejecutar escenario</button></div>{values.length?<div className="stress-visual-grid"><div className="stress-chart-card"><div className="stress-chart-title">Impacto comparativo</div><ResponsiveContainer width="100%" height={280}><BarChart data={values} margin={{top:15,right:15,left:5,bottom:35}}><CartesianGrid stroke="#E2E8F0" vertical={false}/><XAxis dataKey="metric" angle={-18} textAnchor="end" height={55} tick={{fontSize:10,fill:"#64748B"}} axisLine={false} tickLine={false}/><YAxis tick={{fontSize:10,fill:"#64748B"}} axisLine={false} tickLine={false}/><Tooltip/><Bar dataKey="baseline" name="Baseline" fill="#94A3B8" radius={[4,4,0,0]}/><Bar dataKey="stressed" name="Stressed" fill="#EF4444" radius={[4,4,0,0]}/></BarChart></ResponsiveContainer></div><div className="stress-summary"><span>SCENARIO OUTPUT</span><strong>Baseline vs. Stress +{shock}%</strong>{values.slice(0,4).map(x=><div key={x.metric}><b>{x.metric}</b><span>{x.baseline.toLocaleString()} → {x.stressed.toLocaleString()}</span></div>)}<small>Solo se muestran métricas numéricas devueltas por el motor.</small></div></div>:<div className="scenario-empty">Ejecuta un escenario para visualizar el impacto calculado.</div>}</Section>
}

function Engine() {
  const nodes=[['01','Data validation','Quality gate'],['02','Normalization','Canonical facts'],['03','Formulas','Derived metrics'],['04','Scorecard','Risk score'],['05','Rules','Policy evaluation'],['06','Decision','Outcome'],['07','Governance','Approval'],['08','Audit','Evidence ledger'],['09','Action','Human-controlled']]
  return <div className="engine-page"><div className="engine-intro"><div><span>DECISION ENGINE · LOW-CODE</span><h2>Programa cómo RiskIQ decide</h2><p>Pipeline visual de validación, cálculo, política, gobierno y trazabilidad.</p></div><div className="engine-chip">AUDITABLE · HUMAN CONTROL</div></div><div className="engine-node-canvas">{nodes.map(([n,title,detail],i)=><div className="engine-node-wrap" key={n}><div className="engine-node"><span>{n}</span><b>{title}</b><small>{detail}</small></div>{i<nodes.length-1&&<ArrowRight className="engine-node-arrow" size={18}/>}</div>)}</div><Builder/></div>
}

function DataRows({ rows }) {
  return (
    <div className="data-rows">
      {rows.map(([a, b]) => (
        <div key={a}>
          <span>{a}</span>
          <strong>{b}</strong>
        </div>
      ))}
    </div>
  )
}