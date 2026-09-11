import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

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

export default defineConfig({
  plugins: [riskIqRealDataGuard(),react()],
  server: { port: 5173 },
})
