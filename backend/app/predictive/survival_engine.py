from __future__ import annotations
from collections import defaultdict
from typing import Any
from .models import SurvivalCurve,SurvivalPoint

class SurvivalEngine:
    def kaplan_meier(self,rows:list[dict[str,Any]],event_field:str="default",duration_field:str="duration")->SurvivalCurve:
        observations=[]
        for row in rows:
            if row.get(duration_field) is None: continue
            duration=max(0,int(float(row[duration_field])))
            raw=row.get(event_field,False)
            event=1 if str(raw).lower() in {"1","true","yes","bad","default","defaulted"} else 0
            observations.append((duration,event))
        if not observations:return SurvivalCurve(points=[],methodology="kaplan-meier-v1",sample_size=0)
        points=[]; survival=1.0
        for period in sorted({x[0] for x in observations}):
            at_risk=sum(1 for d,_ in observations if d>=period)
            events=sum(1 for d,e in observations if d==period and e)
            if at_risk: survival*=1-(events/at_risk)
            points.append(SurvivalPoint(period=period,at_risk=at_risk,events=events,survival=round(survival,8)))
        return SurvivalCurve(points=points,methodology="kaplan-meier-v1",sample_size=len(observations))
