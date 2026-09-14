import React from 'react'
import {createRoot} from 'react-dom/client'
import App from './RiskOperatingSystem'
import './riskiq-visual-v4.css'
import './workspace-navigation.js'
import './ros-nav-final.css'

// Single production entrypoint. RiskOperatingSystem owns the base shell and
// Builder wires the complete data-to-decision workspace. The final navigation
// layer is imported last so legacy visual overrides cannot fight the accordion.

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
