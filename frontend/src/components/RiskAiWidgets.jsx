import React from 'react'
import { ResponsiveContainer, AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts'

const money = value => '$' + Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })
const pct = value => (Number(value || 0) * 100).toFixed(1) + '%'

export default function RiskAiWidgets({ visualization }) {
  if (!visualization?.type) return null
  const context = visualization.context || ''
  const points = Array.isArray(visualization.data) ? visualization.data : []
  const bullets = Array.isArray(visualization.bullets) ? visualization.bullets : []

  if (visualization.type === 'kpi') {
    return <div className="risk-ai-widget risk-ai-widget-kpi"><span>{visualization.label || context}</span><strong>{visualization.unit === 'pct' ? pct(visualization.value) : visualization.unit === 'money' ? money(visualization.value) : String(visualization.value ?? '—')}</strong></div>
  }

  return <div className="risk-ai-widget">
    {visualization.title && <div className="risk-ai-widget-title">{visualization.title}</div>}
    {visualization.type === 'chart' && points.length ? <div className="risk-ai-widget-chart">
      <ResponsiveContainer width="100%" height={170}>
        <AreaChart data={points}><XAxis dataKey="label" hide/><YAxis hide/><Tooltip/><Area type="monotone" dataKey={visualization.dataKey || 'value'} stroke="#2563eb" fill="#dbeafe" fillOpacity={0.9}/></AreaChart>
      </ResponsiveContainer>
    </div> : null}
    {visualization.type === 'bar' && points.length ? <div className="risk-ai-widget-chart">
      <ResponsiveContainer width="100%" height={170}>
        <BarChart data={points}><XAxis dataKey="label" hide/><YAxis hide/><Tooltip/><Bar dataKey={visualization.dataKey || 'value'} fill="#334155" radius={[4,4,0,0]}/></BarChart>
      </ResponsiveContainer>
    </div> : null}
    {bullets.length ? <ul className="risk-ai-widget-bullets">{bullets.slice(0,5).map((bullet, index) => <li key={index}>{bullet}</li>)}</ul> : null}
  </div>
}
