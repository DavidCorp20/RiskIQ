import React,{useEffect} from 'react'
import {createRoot} from 'react-dom/client'
import App from './RiskOperatingSystem'
import DataUpload from './DataUpload'
import RiskLucideBridge from './RiskLucideBridge'
import './riskiq-tailwind.css'
import './riskiq-portfolio-concentration.css'
import './enterprise-ui-overrides.css'
import RiskIntelligenceProvider from './context/RiskIntelligenceContext'

function LanguageLayer(){
  useEffect(()=>import('./riskiq-spanish-ui.js').then(({installRiskIQLanguage})=>installRiskIQLanguage()),[])
  return null
}

// Single production entrypoint. Navigation state is owned by React.
createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <RiskIntelligenceProvider>
      <LanguageLayer />
      <RiskLucideBridge />
      <App />
      <DataUpload />
    </RiskIntelligenceProvider>
  </React.StrictMode>
)
