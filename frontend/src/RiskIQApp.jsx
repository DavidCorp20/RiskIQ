import RiskCommandCenter from './RiskCommandCenter'
import DecisionEngine from './DecisionEngine'
import './decision-engine.css'

export default function RiskIQApp(){
  return <>
    <RiskCommandCenter />
    <div className="decision-engine-host">
      <DecisionEngine />
    </div>
  </>
}
