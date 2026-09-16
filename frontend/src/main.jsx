import React from 'react'
import {createRoot} from 'react-dom/client'
import App from './RiskOperatingSystem'
import './riskiq-visual-v4.css'
import './workspace-navigation.js'
import './ros-nav-final.css'
import './ros-production-final.css'
import './riskiq-enterprise-system.css'
import './riskiq-nav-accordion.css'

// Single production entrypoint. RiskOperatingSystem owns the base shell.
// The workspace controller is loaded before the final accordion layer so its
// state classes are authoritative over legacy navigation styling.

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
