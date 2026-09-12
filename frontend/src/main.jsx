import React from 'react'
import {createRoot} from 'react-dom/client'
import App from './RiskOperatingSystem'

// One deterministic React entrypoint. The ROS shell owns navigation and layout.
// Deployment marker: 2026-09-12 navigation hierarchy is served from main.
import './risk-os.css'
import './decision-engine-v3.css'
import './riskiq-visual-v4.css'
// Navigation visibility must load last so legacy visual rules cannot reopen menus.
import './ros-visibility.css'
import './ros-nav-accordion.js'

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
