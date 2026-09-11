import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './styles.css'
import './density.css'
import './button-system.css'
import './visual-system.css'
import './builder.css'
import './light-ui.css'

createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>)
