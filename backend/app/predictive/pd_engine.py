from __future__ import annotations
from typing import Any
from .models import PDRating,TransitionMatrix

class PDEngine:
    def ratings(self, matrix:TransitionMatrix, horizon_periods:int=1)->list[PDRating]:
        from .transition_engine import TransitionEngine
        values=TransitionEngine().project_pd(matrix,horizon_periods)
        return [PDRating(entity_id=state,horizon_periods=horizon_periods,pd=value,method="roll-rate-matrix-power",evidence_count=sum(matrix.counts[state].values())) for state,value in values.items()]

    def validation_metrics(self, scores:list[float], labels:list[int])->dict[str,float|int|None]:
        if len(scores)!=len(labels) or not scores: raise ValueError("scores and labels must have equal non-zero length")
        pairs=sorted(zip(scores,labels),key=lambda x:x[0])
        positives=sum(labels); negatives=len(labels)-positives
        auc=None
        if positives and negatives:
            rank_sum=sum(i+1 for i,(_,y) in enumerate(pairs) if y==1)
            auc=(rank_sum-positives*(positives+1)/2)/(positives*negatives)
        ks=None
        if positives and negatives:
            tp=fp=0; ks=0.0
            for _,y in sorted(zip(scores,labels),reverse=True):
                if y: tp+=1
                else: fp+=1
                ks=max(ks,abs(tp/positives-fp/negatives))
        gini=None if auc is None else 2*auc-1
        return {"auc":auc,"gini":gini,"ks":ks,"sample_size":len(labels),"positive_rate":positives/len(labels)}

    def feature_importance(self, rows:list[dict[str,Any]], target:str="default", features:list[str]|None=None)->list[dict[str,Any]]:
        from .models import FeatureImportance
        candidates=features or sorted({key for row in rows for key,value in row.items() if isinstance(value,(int,float)) and not isinstance(value,bool)})
        labels=[]
        for row in rows:
            value=row.get(target)
            if value is None: continue
            labels.append(1 if str(value).lower() in {"1","true","yes","bad","default","defaulted"} else 0)
        if not labels or len(set(labels))<2: return []
        output=[]
        for feature in candidates:
            pairs=[]
            for row in rows:
                if row.get(target) is None or row.get(feature) is None: continue
                try:pairs.append((float(row[feature]),1 if str(row[target]).lower() in {"1","true","yes","bad","default","defaulted"} else 0))
                except (TypeError,ValueError): continue
            if len(pairs)<2: continue
            scores=[x for x,_ in pairs]; ys=[y for _,y in pairs]
            metrics=self.validation_metrics(scores,ys)
            auc=metrics.get("auc")
            if auc is None: continue
            value=abs(float(auc)-0.5)*2
            direction="positive" if sum(s for s,y in pairs if y)/max(1,sum(y for _,y in pairs)) > sum(s for s,y in pairs if not y)/max(1,sum(1-y for _,y in pairs)) else "negative"
            output.append(FeatureImportance(feature=feature,metric="univariate_auc_distance",value=round(value,8),direction=direction,sample_size=len(pairs)).model_dump())
        return sorted(output,key=lambda x:x["value"],reverse=True)

    def empirical_pd(self, rows:list[dict[str,Any]], outcome_field:str="default")->float:
        labels=[]
        for row in rows:
            value=row.get(outcome_field)
            if value is None: continue
            labels.append(1 if str(value).lower() in {"1","true","yes","bad","default","defaulted"} else 0)
        if not labels: raise ValueError("No outcome labels available")
        return sum(labels)/len(labels)
