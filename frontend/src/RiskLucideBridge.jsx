import {useEffect} from 'react'
import {createRoot} from 'react-dom/client'
import {Activity,AlertTriangle,BarChart3,BrainCircuit,ChartNoAxesCombined,ChevronDown,ChevronRight,Database,GitBranch,LayoutDashboard,Menu,Repeat2,ShieldCheck,SlidersHorizontal,Table2,TrendingUp,Workflow} from 'lucide-react'

const icons={
  overview:LayoutDashboard,
  portfolio:Table2,
  analytics:ChartNoAxesCombined,
  concentration:BarChart3,
  cohorts:GitBranch,
  migration:Repeat2,
  stress:SlidersHorizontal,
  decisions:ShieldCheck,
  engine:Workflow,
  quality:Database,
}

function mount(target,Icon,size=16){
  if(!target||target.dataset.lucideMounted==='true')return
  target.dataset.lucideMounted='true'
  target.textContent=''
  createRoot(target).render(<Icon size={size} strokeWidth={1.5} aria-hidden="true" />)
}

function sync(){
  document.querySelectorAll('.ros-nav-icon').forEach(node=>{
    const parent=node.closest('button')
    const label=parent?.querySelector('b')?.textContent||''
    const entry=Object.entries({
      'Centro de mando':'overview','Cartera':'portfolio','Risk Analytics':'analytics','Concentración':'concentration','Vintage & cohortes':'cohorts','Migración':'migration','Stress testing':'stress','Decision Center':'decisions','Decision Engine':'engine','Calidad de datos':'quality'
    }).find(([name])=>name===label)
    if(entry){const Icon=icons[entry[1]];mount(node,Icon,16)}
  })
  document.querySelectorAll('.ros-menu').forEach(node=>mount(node,Menu,18))
  document.querySelectorAll('.side-group-label span:last-child').forEach(node=>{
    const expanded=node.parentElement?.getAttribute('aria-expanded')==='true'
    mount(node,expanded?ChevronDown:ChevronRight,14)
  })

  document.querySelectorAll('.signal-grid > div').forEach((row,index)=>{
    if(row.querySelector('.signal-lucide'))return
    const Icon=index===0?TrendingUp:index===1?AlertTriangle:index===2?Activity:BrainCircuit
    const icon=document.createElement('span')
    icon.className='signal-lucide'
    icon.setAttribute('aria-hidden','true')
    row.prepend(icon)
    mount(icon,Icon,17)
  })

  document.querySelectorAll('.table-wrap tbody tr').forEach(row=>{
    const share=row.children?.[2]
    if(!share||share.dataset.shareBarMounted==='true')return
    const raw=(share.textContent||'').replace('%','').replace(',','.').trim()
    const value=Number(raw)
    if(Number.isFinite(value)){
      share.style.setProperty('--share-width',`${Math.max(0,Math.min(100,value))}%`)
      share.dataset.shareBarMounted='true'
    }
  })
}

export default function RiskLucideBridge(){
  useEffect(()=>{
    sync()
    const observer=new MutationObserver(sync)
    observer.observe(document.getElementById('root'),{subtree:true,childList:true})
    return()=>observer.disconnect()
  },[])
  return null
}
