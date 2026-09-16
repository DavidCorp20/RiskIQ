import React from 'react'
import {createRoot} from 'react-dom/client'
import App from './RiskOperatingSystem'
import './riskiq-visual-v4.css'
import './ros-nav-final.css'
import './ros-production-final.css'
import './riskiq-enterprise-system.css'
import './riskiq-nav-accordion.css'
import './riskiq-design-system.css'

// Single production entrypoint. Navigation state is owned by React.
createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
