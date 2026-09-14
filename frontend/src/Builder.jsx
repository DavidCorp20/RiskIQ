import AnalysisLibrary from './AnalysisLibrary'
import PolicyPortfolioLab from './PolicyPortfolioLab'
import PolicyBacktest from './PolicyBacktest'
import GovernancePanel from './GovernancePanel'

export default function Builder({datasetId=''}){
  return <div className="riskiq-decision-workspace">
    <AnalysisLibrary datasetId={datasetId}/>
    <PolicyPortfolioLab />
    <PolicyBacktest />
    <GovernancePanel />
  </div>
}
