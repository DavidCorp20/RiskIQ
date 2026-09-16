import React,{useEffect} from 'react'
import {createRoot} from 'react-dom/client'
import App from './RiskOperatingSystem'
import './risk-os.css'

function LanguageLayer(){
  useEffect(()=>import('./riskiq-spanish-ui.js').then(({installRiskIQLanguage})=>installRiskIQLanguage()),[])
  return null
}

// Single production entrypoint. Navigation state is owned by React.
createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <LanguageLayer />
    <App />
  </React.StrictMode>
)
