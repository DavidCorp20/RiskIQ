import React,{useEffect} from 'react'
import './formula-help.css'

const HELP=[
 {match:/PAR7/i,title:'PAR7',body:'Fórmula: saldo con 7+ días de mora ÷ exposición total. Ejemplo: $292.000 ÷ $368.050 = 79,3%. Mide deterioro temprano.'},
 {match:/PAR30/i,title:'PAR30',body:'Fórmula: saldo con 30+ días de mora ÷ exposición total. Ejemplo: $246.400 ÷ $368.050 = 66,9%. Es una señal principal de deterioro.'},
 {match:/PAR60/i,title:'PAR60',body:'Fórmula: saldo con 60+ días de mora ÷ exposición total. Ejemplo: $202.100 ÷ $368.050 = 54,9%. Representa deterioro intermedio.'},
 {match:/PAR90/i,title:'PAR90',body:'Fórmula: saldo con 90+ días de mora ÷ exposición total. Ejemplo: $146.800 ÷ $368.050 = 39,9%. Representa mora severa.'},
 {match:/PAR30 pressure/i,title:'PAR30 pressure',body:'Fórmula: to_number(par30) × 500. Ejemplo: PAR30=0,12 → 60 puntos de riesgo. Convierte la mora en puntos del scorecard.'},
 {match:/Utilization/i,title:'Utilization',body:'Fórmula: min(outstanding_balance ÷ max(credit_limit,1),1) × 250. Ejemplo: 82.000 ÷ 120.000 × 250 = 170,8 puntos.'},
 {match:/Trend deterioration/i,title:'Trend deterioration',body:'Fórmula: 100 si trend = "deteriorating"; de lo contrario 0. Ejemplo: una tendencia deteriorada agrega 100 puntos.'},
 {match:/Exposure concentration/i,title:'Exposure concentration',body:'Fórmula: min(outstanding_balance ÷ 100.000,1) × 150. Ejemplo: 82.000 ÷ 100.000 × 150 = 123 puntos.'},
 {match:/Top 3 share/i,title:'Top 3 share',body:'Fórmula: suma de la participación de exposición de los 3 segmentos principales. Ejemplo: 42% + 21% + 14% = 77%.'},
 {match:/HHI/i,title:'HHI',body:'Fórmula: Σ(participación de exposición²) × 10.000. Ejemplo: 50%, 30%, 20% → 2.500 + 900 + 400 = 3.800.'},
 {match:/PAR30 \/ PAR90/i,title:'PAR30 / PAR90',body:'Fórmula: PAR90 ÷ PAR30. Ejemplo: 39,9% ÷ 67,0% = 0,60x. Mide qué parte de la mora 30+ llegó a mora severa.'},
 {match:/Scorecard/i,title:'Scorecard',body:'Funciona como una suma ponderada de factores. Cada fórmula produce puntos y el peso modifica su aporte al score total. Las bandas convierten el score en LOW, WATCH, HIGH o CRITICAL.'},
 {match:/Normalize/i,title:'Normalize',body:'Transforma los datos originales al contrato canónico. Ejemplo: to_number(par30) convierte "0.12" en 0,12 y upper(segment) convierte "premium" en "PREMIUM".'},
 {match:/Risk DSL/i,title:'Risk DSL',body:'Lógica avanzada ejecutada en sandbox. Ejemplo: utilization = exposure ÷ credit_limit; luego una regla puede clasificar HIGH_RISK si par30 ≥ 0,10.'},
 {match:/Formula/i,title:'Formula',body:'Las fórmulas derivan variables a partir de hechos observados. Ejemplo: utilization = outstanding_balance ÷ credit_limit. El resultado queda trazado para auditoría.'},
 {match:/Decision runtime/i,title:'Decision runtime',body:'Ejecuta la misma política sobre un caso de prueba. Flujo: datos → normalización → variables → score → reglas → decisión. En sandbox no ejecuta acciones sobre clientes.'}
]

function textOf(el){return (el.textContent||'').replace(/\s+/g,' ').trim()}
function isUseful(el){
 if(!el||el.nodeType!==1)return false
 const t=textOf(el)
 if(!t||t.length>90)return false
 return ['SPAN','LABEL','H3','H4','STRONG','BUTTON'].includes(el.tagName)
}
function findHelp(text){return HELP.find(x=>x.match.test(text))}

export default function FormulaHelpOverlay(){
 useEffect(()=>{
  const root=document.body
  const scan=()=>{
   const nodes=root.querySelectorAll('label,span,h3,h4,strong,button')
   nodes.forEach(el=>{
    if(!isUseful(el))return
    const help=findHelp(textOf(el))
    if(!help||el.querySelector(':scope > .ri-inline-info'))return
    const info=document.createElement('button')
    info.type='button';info.className='ri-inline-info';info.setAttribute('aria-label',`Información sobre ${help.title}`)
    info.setAttribute('data-help',help.body);info.setAttribute('data-title',help.title);info.textContent='i'
    el.appendChild(info)
   })
  }
  scan()
  const observer=new MutationObserver(()=>scan())
  observer.observe(root,{subtree:true,childList:true,characterData:true})
  return()=>observer.disconnect()
 },[])
 return null
}
