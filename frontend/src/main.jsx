import React from 'react'
import {createRoot} from 'react-dom/client'
import App from './RiskOperatingSystem'
import './riskiq-visual-v4.css'
import './workspace-navigation.js'

// Single production entrypoint. RiskOperatingSystem owns the base shell and
// Builder wires the complete data-to-decision workspace. Keep one visual
// polish layer for Analytics and sidebar category styling; avoid reintroducing
// duplicate CSS layers with competing !important rules.

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
