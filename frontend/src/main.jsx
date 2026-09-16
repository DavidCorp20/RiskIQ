import React from 'react'
import {createRoot} from 'react-dom/client'
import App from './RiskOperatingSystem'
import './riskiq-visual-v4.css'
import './ros-nav-final.css'
import './ros-production-final.css'
import './riskiq-enterprise-system.css'

// Single production entrypoint. RiskOperatingSystem owns the application shell
// and navigation state. The enterprise stylesheet is the final visual layer.

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
