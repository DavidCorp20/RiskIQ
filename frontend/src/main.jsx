import React from 'react'
import {createRoot} from 'react-dom/client'
import App from './RiskOperatingSystem'
import './riskiq-visual-v4.css'
import './workspace-navigation.js'
import './ros-nav-final.css'
import './ros-production-final.css'

// Single production entrypoint. RiskOperatingSystem owns the base shell.
// The final stylesheet is intentionally last: it neutralizes browser defaults
// and legacy drift without changing the application architecture.

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
