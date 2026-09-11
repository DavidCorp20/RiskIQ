import React, { useMemo, useState } from 'react'

const FIELDS = [
  { value: 'par7', label: 'PAR7' },
  { value: 'par30', label: 'PAR30' },
  { value: 'par60', label: 'PAR60' },
  { value: 'par90', label: 'PAR90' },
  { value: 'outstanding_balance', label: 'Exposición' },
  { value: 'priority_score', label: 'Priority score' },
  { value: 'segment', label: 'Segmento' },
  { value: 'product', label: 'Producto' },
  { value: 'trend', label: 'Tendencia' },
]

const OPERATORS = [
  ['gt', 'mayor que'], ['gte', 'mayor o igual que'], ['lt', 'menor que'],
  ['lte', 'menor o igual que'], ['eq', 'igual a'], ['neq', 'distinto de'],
]

const blankCondition = () => ({ field: 'par30', operator: 'gt', value: '0.10' })

export default function DecisionEngine({ current = {}, onApply }) {
  const [name, setName] = useState('Early Delinquency')
  const [logic, setLogic] = useState('AND')
  const [conditions, setConditions] = useState([blankCondition()])
  const [outcome, setOutcome] = useState('HIGH_RISK')
  const [priority, setPriority] = useState('1')
  const [action, setAction] = useState('Crear revisión humana')
  const [saved, setSaved] = useState(false)

  const preview = useMemo(() => ({
    policy_id: 'POL-DRAFT', version: 1, name,
    logic, conditions, outcome, priority: Number(priority) || 0, action,
    approval: 'human_review', executed: false,
  }), [name, logic, conditions, outcome, priority, action])

  const updateCondition = (index, patch) => setConditions(items => items.map((item, i) => i === index ? { ...item, ...patch } : item))

  return (
    <section className="decision-engine" aria-label="Decision Engine">
      <div className="decision-engine__header">
        <div>
          <span className="section-eyebrow">DECISION ENGINE</span>
          <h2>Políticas configurables</h2>
          <p>Construye decisiones reutilizables sin hardcodear reglas. El motor produce evidencia, prioridad y una acción propuesta para revisión humana.</p>
        </div>
        <div className="decision-engine__status">LOW-CODE · HUMAN REVIEW</div>
      </div>

      <div className="decision-engine__grid">
        <div className="decision-engine__builder">
          <label>Nombre de política<input value={name} onChange={e => setName(e.target.value)} /></label>

          <div className="builder-block">
            <div className="builder-block__title"><strong>WHEN</strong><span>{conditions.length} condición{conditions.length === 1 ? '' : 'es'}</span></div>
            {conditions.map((condition, index) => (
              <React.Fragment key={index}>
                {index > 0 && <div className="logic-row"><select value={logic} onChange={e => setLogic(e.target.value)}><option>AND</option><option>OR</option></select></div>}
                <div className="condition-row">
                  <select value={condition.field} onChange={e => updateCondition(index, { field: e.target.value })}>{FIELDS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}</select>
                  <select value={condition.operator} onChange={e => updateCondition(index, { operator: e.target.value })}>{OPERATORS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
                  <input value={condition.value} onChange={e => updateCondition(index, { value: e.target.value })} aria-label={`Valor condición ${index + 1}`} />
                  {conditions.length > 1 && <button className="button button--ghost" onClick={() => setConditions(items => items.filter((_, i) => i !== index))}>Quitar</button>}
                </div>
              </React.Fragment>
            ))}
            <button className="button button--secondary" onClick={() => setConditions(items => [...items, blankCondition()])}>+ Agregar condición</button>
          </div>

          <div className="builder-block">
            <div className="builder-block__title"><strong>THEN</strong><span>Resultado operativo</span></div>
            <div className="then-grid">
              <label>Nivel<select value={outcome} onChange={e => setOutcome(e.target.value)}><option value="LOW_RISK">LOW RISK</option><option value="WATCH">WATCH</option><option value="HIGH_RISK">HIGH RISK</option><option value="CRITICAL">CRITICAL</option><option value="REVIEW">REVIEW</option></select></label>
              <label>Prioridad<input type="number" min="1" max="5" value={priority} onChange={e => setPriority(e.target.value)} /></label>
              <label>Acción propuesta<input value={action} onChange={e => setAction(e.target.value)} /></label>
            </div>
          </div>

          <div className="engine-actions">
            <button className="button button--primary" onClick={() => { setSaved(true); onApply?.(preview) }}>Guardar política</button>
            <button className="button button--secondary" onClick={() => setSaved(false)}>Probar política</button>
            {saved && <span className="save-confirm">Borrador preparado · versión 1</span>}
          </div>
        </div>

        <aside className="decision-engine__preview">
          <span className="section-eyebrow">POLICY PREVIEW</span>
          <h3>{name || 'Nueva política'}</h3>
          <div className="policy-flow">
            <div><b>WHEN</b>{conditions.map((c, i) => <span key={i}>{FIELDS.find(f => f.value === c.field)?.label} {OPERATORS.find(o => o[0] === c.operator)?.[1]} {c.value}</span>)}</div>
            <div className="policy-arrow">↓</div>
            <div><b>THEN</b><span>{outcome}</span><span>Prioridad {priority}</span><span>{action}</span></div>
          </div>
          <div className="evidence-box"><strong>Gobernanza</strong><p>La decisión conserva política, versión, condiciones, evidencia y estado de ejecución. Las acciones no se ejecutan automáticamente.</p></div>
          <div className="evidence-box"><strong>Datos actuales</strong><p>PAR30: {typeof current.par30 === 'number' ? `${(current.par30 * 100).toFixed(1)}%` : '—'} · Exposición: {current.outstanding_balance ?? '—'}</p></div>
        </aside>
      </div>
    </section>
  )
}
