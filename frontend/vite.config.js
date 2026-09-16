import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

function riskIqRealDataGuard(){
  return {
    name: 'riskiq-real-data-guard',
    enforce: 'pre',
    transform(code, id){
      if(!id.endsWith('/src/App.jsx')) return null
      const withoutDemo=code.replace(/const demoCurrent=.*?\n/,'')
      const withoutAnalysisFallback=withoutDemo.replace('analysis=result?.analysis||demoAnalysis','analysis=result?.analysis||null')
      return withoutAnalysisFallback===code?null:{code:withoutAnalysisFallback,map:null}
    },
  }
}

function riskIqLegacyStyleGuard(){
  const legacy = /import\s+['\"]\.\/(?:risk-os|riskiq-visual-v4|ros-nav-final|ros-production-final|riskiq-enterprise-system|riskiq-nav-accordion|riskiq-design-system|riskiq-readability)\.css['\"];?/g
  return {
    name: 'riskiq-legacy-style-guard',
    enforce: 'pre',
    transform(code, id){
      if(!id.endsWith('.jsx')) return null
      const next=code.replace(legacy,'')
      return next===code?null:{code:next,map:null}
    },
  }
}

export default defineConfig({
  plugins: [riskIqRealDataGuard(),riskIqLegacyStyleGuard(),react(),tailwindcss()],
  server: { port: 5173 },
})
