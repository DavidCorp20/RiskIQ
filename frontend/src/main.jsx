import React from 'react'
import {createRoot} from 'react-dom/client'
import App from './RiskOperatingSystem'
import FormulaHelpOverlay from './FormulaHelpOverlay'

// RiskIQ uses one visual system for the Risk Operating System.
// Legacy dashboard styles are intentionally not loaded here because their
// global selectors conflict with the ROS surface and typography.
import './risk-os.css'
import './decision-engine-v3.css'
import './formula-help.css'
import './riskiq-final.css'

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <>
      <App />
      <FormulaHelpOverlay />
    </>
  </React.StrictMode>
)
