import React,{useEffect} from 'react'
import {createRoot} from 'react-dom/client'
import App from './RiskOperatingSystem'
import { RiskIntelligenceProvider } from './RiskIntelligenceProvider'
import DataUpload from './DataUpload'
import RiskLucideBridge from './RiskLucideBridge'
import './riskiq-tailwind.css'
import './riskiq-portfolio-concentration.css'
import './enterprise-ui-overrides.css'

function LanguageLayer(){
  useEffect(()=>import('./riskiq-spanish-ui.js').then(({installRiskIQLanguage})=>installRiskIQLanguage()),[])
  return null
}

// Single production entrypoint. Navigation state is owned by React.
createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <LanguageLayer />
    <RiskLucideBridge />
    <RiskIntelligenceProvider>
      <App />
    </RiskIntelligenceProvider>
    <DataUpload />
  </React.StrictMode>
)
