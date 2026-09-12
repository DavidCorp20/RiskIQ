import PolicyPortfolioLab from './PolicyPortfolioLab'
import PolicyBacktest from './PolicyBacktest'
import GovernancePanel from './GovernancePanel'

export default function Builder(){
  return <div className="riskiq-decision-workspace">
    <PolicyPortfolioLab />
    <PolicyBacktest />
    <GovernancePanel />
  </div>
}
