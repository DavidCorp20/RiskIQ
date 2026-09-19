import React from 'react'
const labels={PENDING:'Pendiente',IN_PROGRESS:'En curso',COMPLETED:'Completada',CANCELLED:'Cancelada'}
export default function ActionStatusBadge({action}){if(!action)return <span className="risk-action-badge risk-action-badge--none">Sin acción</span>;const s=String(action.status||'PENDING').toUpperCase(),ticket=action.external_ticket_id||action.freshservice_ticket_id;return <span className={'risk-action-badge risk-action-badge--'+s.toLowerCase()} title={ticket?'Freshservice: '+ticket:'Sin ticket'}>{ticket?'FS · '+(labels[s]||s):(labels[s]||s)}</span>}
