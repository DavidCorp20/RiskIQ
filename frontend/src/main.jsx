import React from 'react'
import {createRoot} from 'react-dom/client'
import App from './RiskOperatingSystem'

// RiskIQ has one deterministic React visual entrypoint.
// Do not mount DOM-mutating enhancers or competing global visual layers here.
import './risk-os.css'
import './decision-engine-v3.css'

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
