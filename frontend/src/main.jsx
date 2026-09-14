import React from 'react'
import {createRoot} from 'react-dom/client'
import App from './RiskCommandCenter'

// Stable production entrypoint. The command center owns navigation and layout.
import './risk-command-center.css'
import './decision-engine-v3.css'
import './riskiq-visual-v4.css'
import './ros-visibility.css'
import './ros-nav-accordion.js'
import './workspace-navigation.css'
import './workspace-navigation.js'

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
