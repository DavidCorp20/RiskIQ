import {useEffect,useState} from 'react'
import AnalysisLibrary from './AnalysisLibrary'
import PolicyPortfolioLab from './PolicyPortfolioLab'
import PolicyBacktest from './PolicyBacktest'
import GovernancePanel from './GovernancePanel'

export default function Builder({datasetId=''}){
  const [activeDataset,setActiveDataset]=useState(datasetId)
  useEffect(()=>{
    if(datasetId)return
    try{setActiveDataset(JSON.parse(localStorage.getItem('riskiq.activeDataset')||'null')?.dataset_id||'')}catch{setActiveDataset('')}
  },[datasetId])
  return <div className="riskiq-decision-workspace">
    <AnalysisLibrary datasetId={activeDataset}/>
    <PolicyPortfolioLab />
    <PolicyBacktest />
    <GovernancePanel />
  </div>
}
