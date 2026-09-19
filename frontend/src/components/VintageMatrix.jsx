import React from 'react'

export default function VintageMatrix({ rows = [], columns = [], title = 'Vintage matrix' }) {
  return (
    <section className="portfolio-panel">
      <div className="portfolio-panel-heading">
        <div><span>VINTAGE</span><h3>{title}</h3></div>
        <small>{rows.length} cohorts</small>
      </div>
      {!rows.length || !columns.length ? (
        <div className="portfolio-empty">No vintage evidence available.</div>
      ) : (
        <div className="portfolio-table-wrap">
          <table className="portfolio-vintage-table">
            <thead>
              <tr>
                <th>Cohort</th>
                {columns.map(column => <th key={column.key ?? column}>{column.label ?? column}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={row.id ?? row.cohort ?? index}>
                  <th>{row.cohort ?? row.label ?? '—'}</th>
                  {columns.map(column => {
                    const key = column.key ?? column
                    const cell = row[key]
                    const display = typeof cell === 'object' ? cell.displayValue ?? cell.value ?? '—' : cell ?? '—'
                    return <td key={key}>{display}</td>
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
