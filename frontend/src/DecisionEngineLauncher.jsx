import {useState} from 'react'
import RiskCommandCenter from './RiskCommandCenter'
import DecisionEngine from './DecisionEngine'
import './decision-engine.css'
import './decision-engine-launcher.css'

export default function DecisionEngineLauncher(){
 const [open,setOpen]=useState(false)
 return <>
  <RiskCommandCenter/>
  <button className="de-launch" onClick={()=>setOpen(true)} aria-label="Abrir programador de decisiones"><span>⌘</span><div><b>Programar decisiones</b><small>Decision Engine · Low-Code</small></div></button>
  {open&&<div className="de-modal" role="dialog" aria-modal="true" aria-label="Programador de decisiones">
   <div className="de-modal__bar"><div><span>DECISION ENGINE</span><h2>Programador de políticas</h2><p>Diseña, prueba y versiona lógica de decisión sin modificar código.</p></div><button className="de-close" onClick={()=>setOpen(false)}>Cerrar</button></div>
   <div className="de-modal__body"><DecisionEngine/></div>
  </div>}
 </>
}
