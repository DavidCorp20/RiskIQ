import React from 'react'
import {createRoot} from 'react-dom/client'
import App from './RiskOperatingSystem'

// One deterministic React entrypoint. The ROS shell owns navigation and layout.
import './risk-os.css'
import './decision-engine-v3.css'
import './ros-visibility.css'
import './riskiq-visual-v4.css'
import './ros-nav-accordion.js'

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
