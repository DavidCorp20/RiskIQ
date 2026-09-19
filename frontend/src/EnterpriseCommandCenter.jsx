import { useMemo } from 'react'
import {
  AreaChart, Area, BarChart, Bar, CartesianGrid, Cell, ComposedChart,
  Line, ResponsiveContainer, Sankey, Tooltip, XAxis, YAxis
} from 'recharts'
import { Activity, ArrowUpRight, Database, ShieldAlert, TrendingDown, TrendingUp } from 'lucide-react'

const pct = v => `${(Number(v || 0) * 100).toFixed(1)}%`
const money = v => `$${Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`
const safe = v => Number.isFinite(Number(v)) ? Number(v) : 0

const COLORS = { primary:'#2563EB', navy:'#0F172A', critical:'#EF4444', warning:'#F97316', healthy:'#10B981', info:'#3B82F6', grid:'#E2E8F0', muted:'#64748B' }

function Card({ eyebrow, title, children, className='' }) {
  return <section className={`enterprise-card ${className}`}>
    <div className="enterprise-card-head">
      <div><span>{eyebrow}</span><h3>{title}</h3></div>
    </div>
    {children}
  </section>
}

function EmptyChart({ message }) {
  return <div className="enterprise-empty-chart"><Database size={18}/><span>{message}</span></div>
}

function TooltipContent({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return <div className="enterprise-tooltip"><b>{label}</b>{payload.map((p,i)=><div key={i}><span>{p.name}</span><strong>{typeof p.value==='number' && p.dataKey?.includes('rate') ? pct(p.value) : p.value}</strong></div>)}</div>
}

function buildTrend(history, snap) {
  const rows = history?.snapshots || history?.trend || history?.items || []
  if (Array.isArray(rows) && rows.length) {
    return rows.map((x,i)=>({
      label:x.snapshot_date || x.date || x.as_of || x.period || `Corte ${i+1}`,
      exposure:safe(x.outstanding_balance ?? x.exposure ?? x.balance),
      par30:safe(x.par30 ?? x.par30_ratio),
      par90:safe(x.par90 ?? x.par90_ratio)
    }))
  }
  const previous=history?.previous_snapshot || history?.previous || {}
  const current=history?.current_snapshot || history?.current || snap || {}
  const out=[]
  if (previous && Object.keys(previous).length) out.push({label:history?.previous_snapshot_date||'Anterior',exposure:safe(previous.outstanding_balance ?? previous.exposure),par30:safe(previous.par30),par90:safe(previous.par90)})
  out.push({label:history?.current_snapshot_date||'Actual',exposure:safe(current.outstanding_balance ?? current.exposure),par30:safe(current.par30),par90:safe(current.par90)})
  return out.filter(x=>x.exposure||x.par30||x.par90)
}

function buildFlow(adv, snap) {
  const migration=adv?.migration || {}
  const transitions=migration.transition_balances || migration.transitions || migration.roll_rate_by_balance || []
  const labels=['Corriente','PAR30','PAR60','PAR90','Castigo']
  if (!Array.isArray(transitions) || !transitions.length) return null
  const links=[]
  transitions.forEach(t=>{
    const from=t.from || t.source || t.from_bucket
    const to=t.to || t.target || t.to_bucket
    const value=safe(t.balance ?? t.exposure ?? t.amount)
    if(from && to && value>0) links.push({source:labels.indexOf(from)>=0?labels.indexOf(from):from,target:labels.indexOf(to)>=0?labels.indexOf(to):to,value})
  })
  if(!links.length) return null
  const nodes=labels.map(name=>({name}))
  const normalized=links.map(x=>({...x,source:typeof x.source==='number'?x.source:0,target:typeof x.target==='number'?x.target:1}))
  return {nodes,links:normalized}
}

export default function EnterpriseCommandCenter({ snap={}, ri={}, concentration=[], priorities=[], history=null, adv={}, vintage={}, quality={}, onGo }) {
  const trend=useMemo(()=>buildTrend(history,snap),[history,snap])
  const flows=useMemo(()=>buildFlow(adv,snap),[adv,snap])
  const cohorts=Array.isArray(vintage?.vintages) ? vintage.vintages : []
  const maxExposure=Math.max(...concentration.map(x=>safe(x.exposure_share)),0.01)
  const severity=(key)=>key==='par90' ? (safe(snap.par90)>=.02?'critical':safe(snap.par90)>=.01?'warning':'healthy') : key==='par30' ? (safe(snap.par30)>=.10?'critical':safe(snap.par30)>=.05?'warning':'healthy') : 'info'
  const actions=priorities.slice(0,4)

  return <div className="enterprise-dashboard">
    <div className="enterprise-hero">
      <div>
        <div className="enterprise-kicker"><Activity size={13}/> CREDIT RISK / COMMAND CENTER</div>
        <h2>{ri?.posture?.label || 'Portfolio risk command center'}</h2>
        <p>{ri?.interpretation || 'Evidence-first portfolio monitoring with deterministic risk analytics and governed decisions.'}</p>
      </div>
      <div className="enterprise-hero-status">
        <span>ENGINE STATUS</span><b>READY</b><small>{quality?.score ? `Data confidence ${quality.score}/100` : 'Deterministic evidence engine'}</small>
      </div>
    </div>

    <div className="enterprise-kpis">
      <Kpi label="Total Exposure" value={money(snap.outstanding_balance)} detail="Outstanding balance" tone="info"/>
      <Kpi label="Active Loans" value={Number(snap.active_loans||0).toLocaleString()} detail="Portfolio volume" tone="info"/>
      <Kpi label="PAR30" value={pct(snap.par30)} detail={money(ri?.materiality?.bad_balance_30_plus)} tone={severity('par30')}/>
      <Kpi label="PAR60" value={pct(snap.par60)} detail={money(ri?.materiality?.bad_balance_60_plus)} tone="warning"/>
      <Kpi label="PAR90" value={pct(snap.par90)} detail={money(ri?.materiality?.bad_balance_90_plus)} tone={severity('par90')}/>
      <Kpi label="Data Confidence" value={quality?.score ? `${quality.score}/100` : '—'} detail={quality?.confidence || 'Evidence quality'} tone="info"/>
    </div>

    <div className="enterprise-grid enterprise-grid-8-4">
      <Card eyebrow="PORTFOLIO TREND" title="Origination & deterioration" className="enterprise-chart-card">
        {trend.length>1 ? <ResponsiveContainer width="100%" height={290}>
          <ComposedChart data={trend} margin={{top:12,right:12,left:0,bottom:0}}>
            <CartesianGrid stroke={COLORS.grid} vertical={false}/>
            <XAxis dataKey="label" tick={{fontSize:11,fill:COLORS.muted}} axisLine={false} tickLine={false}/>
            <YAxis yAxisId="money" tick={{fontSize:11,fill:COLORS.muted}} axisLine={false} tickLine={false}/>
            <YAxis yAxisId="rate" orientation="right" tickFormatter={v=>`${(v*100).toFixed(0)}%`} tick={{fontSize:11,fill:COLORS.muted}} axisLine={false} tickLine={false}/>
            <Tooltip content={<TooltipContent/>}/>
            <Area yAxisId="money" type="monotone" dataKey="exposure" name="Exposure" fill="#DBEAFE" stroke={COLORS.primary} fillOpacity={.8}/>
            <Line yAxisId="rate" type="monotone" dataKey="par30" name="PAR30" stroke={COLORS.warning} strokeWidth={2.5} dot={{r:3}}/>
            <Line yAxisId="rate" type="monotone" dataKey="par90" name="PAR90" stroke={COLORS.critical} strokeWidth={2.5} dot={{r:3}}/>
          </ComposedChart>
        </ResponsiveContainer> : <EmptyChart message="Se necesitan al menos dos cortes comparables para mostrar tendencia. RiskIQ no inventa una serie temporal."/>}
      </Card>

      <Card eyebrow="RISK POSTURE" title="Current exposure profile">
        <div className="posture-stack">
          {[
            ['PAR30',snap.par30,ri?.materiality?.bad_balance_30_plus,'warning'],
            ['PAR60',snap.par60,ri?.materiality?.bad_balance_60_plus,'warning'],
            ['PAR90',snap.par90,ri?.materiality?.bad_balance_90_plus,'critical']
          ].map(([label,rate,balance,tone])=><div className="posture-row" key={label}>
            <div><span>{label}</span><b>{pct(rate)}</b></div>
            <div className="posture-track"><i className={tone} style={{width:`${Math.min(100,safe(rate)*500)}%`}}/></div>
            <small>{money(balance)} exposed</small>
          </div>)}
        </div>
        <div className="enterprise-note"><ShieldAlert size={16}/><span>{ri?.posture?.label || 'Current risk posture'} · severity is based on calculated portfolio evidence.</span></div>
      </Card>
    </div>

    <div className="enterprise-grid enterprise-grid-7-5">
      <Card eyebrow="CONCENTRATION" title="Where risk is concentrated">
        {concentration.length ? <ResponsiveContainer width="100%" height={280}>
          <BarChart data={concentration.slice(0,8)} layout="vertical" margin={{left:18,right:16}}>
            <CartesianGrid stroke={COLORS.grid} horizontal={false}/>
            <XAxis type="number" tickFormatter={v=>`${(v*100).toFixed(0)}%`} tick={{fontSize:10,fill:COLORS.muted}} axisLine={false} tickLine={false}/>
            <YAxis type="category" dataKey="name" width={110} tick={{fontSize:11,fill:'#334155'}} axisLine={false} tickLine={false}/>
            <Tooltip content={<TooltipContent/>}/>
            <Bar dataKey="exposure_share" name="Exposure share" radius={[0,4,4,0]} barSize={18}>{concentration.slice(0,8).map((x,i)=><Cell key={i} fill={i===0?COLORS.primary:'#94A3B8'}/>)}</Bar>
          </BarChart>
        </ResponsiveContainer> : <EmptyChart message="No hay una dimensión de concentración suficiente."/>}
      </Card>

      <Card eyebrow="TOP RISK SIGNALS" title="Priority review queue">
        <div className="enterprise-actions">{actions.length ? actions.map((x,i)=><div className="enterprise-action" key={i}>
          <span className={i===0?'critical':''}>{String(x.rank||i+1).padStart(2,'0')}</span><div><b>{x.title}</b><small>{x.why || 'Calculated evidence available for review.'}</small></div><ArrowUpRight size={15}/>
        </div>) : <EmptyChart message="No priority signals calculated." />}</div>
      </Card>
    </div>

    <div className="enterprise-grid enterprise-grid-6-6">
      <Card eyebrow="VINTAGE / COHORTS" title="Cohort risk profile">
        {cohorts.length ? <ResponsiveContainer width="100%" height={280}>
          <BarChart data={cohorts.slice(0,12)} margin={{left:0,right:8}}>
            <CartesianGrid stroke={COLORS.grid} vertical={false}/>
            <XAxis dataKey="vintage" tick={{fontSize:10,fill:COLORS.muted}} axisLine={false} tickLine={false}/>
            <YAxis tickFormatter={v=>`${(v*100).toFixed(0)}%`} tick={{fontSize:10,fill:COLORS.muted}} axisLine={false} tickLine={false}/>
            <Tooltip content={<TooltipContent/>}/>
            <Bar dataKey="par30" name="PAR30" fill={COLORS.warning} radius={[4,4,0,0]}/>
            <Bar dataKey="par90" name="PAR90" fill={COLORS.critical} radius={[4,4,0,0]}/>
          </BarChart>
        </ResponsiveContainer> : <EmptyChart message="Se requieren cohortes de originación para construir esta vista."/>}
      </Card>

      <Card eyebrow="MIGRATION / ROLL RATES" title="Observed portfolio flow">
        {flows ? <ResponsiveContainer width="100%" height={280}>
          <Sankey data={flows} nodePadding={28} nodeWidth={12} linkCurvature={.45} margin={{left:8,right:8,top:10,bottom:10}}>
            <Tooltip/>
          </Sankey>
        </ResponsiveContainer> : <EmptyChart message="La migración requiere snapshots consecutivos por crédito. Se muestra solo cuando existe evidencia observada."/>}
      </Card>
    </div>

    <Card eyebrow="EXECUTIVE ACTION" title="Decision focus">
      <div className="enterprise-decision">
        <div><TrendingDown size={18}/><div><b>{actions[0]?.title || 'Build the evidence base'}</b><span>{actions[0]?.why || 'Validate concentration, trajectory and materiality before changing policy or collections strategy.'}</span></div></div>
        <button onClick={()=>onGo?.('decisions')}>Open Decision Center <ArrowUpRight size={15}/></button>
      </div>
    </Card>
  </div>
}

function Kpi({label,value,detail,tone}) {
  return <div className={`enterprise-kpi ${tone}`}><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>
}
