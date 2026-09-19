import React from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function RatingDistribution({ data = [], title = 'Rating distribution' }) {
  return (
    <section className="portfolio-panel">
      <div className="portfolio-panel-heading">
        <div><span>STRUCTURE</span><h3>{title}</h3></div>
        <small>{data.length} buckets</small>
      </div>

      {!data.length ? (
        <div className="portfolio-empty">No rating evidence available.</div>
      ) : (
        <div className="portfolio-chart">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" />
              <XAxis dataKey="rating" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="exposure" name="Exposure" radius={[5, 5, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  )
}
