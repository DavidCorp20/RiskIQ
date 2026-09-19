from __future__ import annotations
from collections import defaultdict
from typing import Any
from .models import TransitionMatrix

STATES=("current","early_1_29","early_30_59","late_60_89","hard_90_plus")

def bucket(dpd: float) -> str:
    if dpd < 1:return "current"
    if dpd < 30:return "early_1_29"
    if dpd < 60:return "early_30_59"
    if dpd < 90:return "late_60_89"
    return "hard_90_plus"

class TransitionEngine:
    def build_matrix(self, rows:list[dict[str,Any]])->TransitionMatrix:
        histories=defaultdict(list)
        for row in rows:
            loan=str(row.get("loan_id") or row.get("customer_id") or "")
            if loan: histories[loan].append(row)
        counts={s:{t:0 for t in STATES} for s in STATES}
        sample=0
        for history in histories.values():
            ordered=sorted(history,key=lambda x:str(x.get("snapshot_date") or ""))
            for prev,curr in zip(ordered,ordered[1:]):
                s=bucket(float(prev.get("dpd",0) or 0)); t=bucket(float(curr.get("dpd",0) or 0))
                counts[s][t]+=1; sample+=1
        probabilities={}
        for s in STATES:
            total=sum(counts[s].values())
            probabilities[s]={t:(counts[s][t]/total if total else (1.0 if s==t else 0.0)) for t in STATES}
        return TransitionMatrix(states=list(STATES),probabilities=probabilities,counts=counts,sample_size=sample,methodology="observed-roll-rate-transition-matrix-v1")

    def project_pd(self,matrix:TransitionMatrix,horizon_periods:int=1)->dict[str,float]:
        if horizon_periods<1: raise ValueError("horizon_periods must be >= 1")
        m=[[matrix.probabilities[s][t] for t in matrix.states] for s in matrix.states]
        p=self._power(m,horizon_periods)
        hard=matrix.states.index("hard_90_plus")
        return {matrix.states[i]:round(p[i][hard],8) for i in range(len(matrix.states))}

    @staticmethod
    def _multiply(a,b):
        n=len(a); return [[sum(a[i][k]*b[k][j] for k in range(n)) for j in range(n)] for i in range(n)]
    def _power(self,m,n):
        size=len(m); result=[[1.0 if i==j else 0.0 for j in range(size)] for i in range(size)]
        base=m
        while n:
            if n%2: result=self._multiply(result,base)
            base=self._multiply(base,base); n//=2
        return result
