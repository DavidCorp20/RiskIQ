export default function EvidenceMethodology({ compact = false }) {
  return (
    <aside className={`ri-evidence-methodology ${compact ? 'compact' : ''}`} aria-label="Metodología de evidencia">
      <div className="ri-evidence-methodology-mark">E</div>
      <div>
        <span className="ri-evidence-methodology-kicker">GUARDRAIL METODOLÓGICO</span>
        <strong>Evidencia determinística, ponderada por exposición</strong>
        <p>RiskIQ calcula señales sobre datos observados y balances reales de la cartera. Los Roll Rates son transiciones observadas y el EWS no representa una probabilidad predictiva.</p>
      </div>
      <style>{`.ri-evidence-methodology{display:flex;gap:12px;align-items:flex-start;padding:15px 17px;border:1px solid #d8e0e8;border-radius:13px;background:#f7f9fb;color:#26374a}.ri-evidence-methodology.compact{padding:12px 14px}.ri-evidence-methodology-mark{width:24px;height:24px;display:grid;place-items:center;border-radius:7px;background:#e8eef5;color:#40546a;font-size:11px;font-weight:900;flex:0 0 auto}.ri-evidence-methodology-kicker{display:block;font-size:9px;letter-spacing:.13em;font-weight:900;color:#718094;margin-bottom:4px}.ri-evidence-methodology strong{display:block;font-size:12px}.ri-evidence-methodology p{margin:5px 0 0;font-size:11px;line-height:1.5;color:#687789}`}</style>
    </aside>
  )
}
