import React from 'react'

export default function VintageMatrix({ vintage = [], title = 'Vintage matrix' }) {
  return (
    <section className="portfolio-panel">
      <div className="portfolio-panel-heading">
        <div><span>VINTAGE</span><h3>{title}</h3></div>
        <small>{vintage.length} cohorts</small>
      </div>

      {!vintage.length ? (
        <div className="portfolio-empty">No vintage evidence available.</div>
      ) : (
        <div className="portfolio-table-wrap">
          <table className="portfolio-vintage-table">
            <thead>
              <tr>
                <th>Cohort</th>
                <th>PAR30</th>
                <th>Exposure</th>
              </tr>
            </thead>
            <tbody>
              {vintage.map((cell) => (
                <tr key={cell.vintage}>
                  <th>{cell.vintage}</th>
                  <td>{cell.formatted_value}</td>
                  <td>{cell.formatted_exposure}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
