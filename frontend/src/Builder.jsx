import PolicyPortfolioLab from './PolicyPortfolioLab'
import PolicyBacktest from './PolicyBacktest'

export default function Builder(){
  return <div className="riskiq-decision-workspace">
    <PolicyPortfolioLab />
    <PolicyBacktest />
  </div>
}
