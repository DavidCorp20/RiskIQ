import { Download, RefreshCw, CalendarDays, Filter } from 'lucide-react'

export default function PortfolioToolbar({ data, segment, cutoffDate, onSegmentChange, onCutoffChange, onRefresh, onExport, loading }) {
  const segments = data?.filters?.segments || []
  const dates = data?.filters?.cutoff_dates || []
  return <div className="portfolio-toolbar">
    <div className="portfolio-toolbar-title"><span>PORTFOLIO / C-LEVEL</span><strong>{data?.snapshot_date || 'Corte actual'}</strong></div>
    <div className="portfolio-toolbar-filters">
      <label><span><Filter size={11}/> Segmento</span><select value={segment} onChange={e=>onSegmentChange(e.target.value)}><option value="">Todos</option>{segments.map(x=><option key={x} value={x}>{x}</option>)}</select></label>
      <label><span><CalendarDays size={11}/> Fecha de corte</span><select value={cutoffDate} onChange={e=>onCutoffChange(e.target.value)}><option value="">Último corte</option>{dates.slice().reverse().map(x=><option key={x} value={x}>{x}</option>)}</select></label>
    </div>
    <div className="portfolio-toolbar-actions"><button onClick={onRefresh} disabled={loading}><RefreshCw size={15} className={loading?'portfolio-spin':''}/> Actualizar</button><button className="portfolio-toolbar-primary" onClick={onExport}><Download size={15}/> Export JSON</button></div>
  </div>
}