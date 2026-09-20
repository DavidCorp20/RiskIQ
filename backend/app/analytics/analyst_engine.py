from __future__ import annotations
from typing import Any
import numpy as np
import pandas as pd
from app.analytics.analyst_models import AnalystFilter, AnalystQuery, AnalystResult
from app.analytics.analyst_registry import get_measure

class AnalystEngine:
    """Safe declarative query engine; never executes user supplied Python/SQL/code."""
    def execute(self, query: AnalystQuery, dataset: pd.DataFrame) -> AnalystResult:
        if not isinstance(dataset,pd.DataFrame): raise TypeError("dataset must be a pandas DataFrame")
        frame=dataset.copy(deep=False)
        self._validate(query,frame)
        filtered=self._filters(frame,query.filters)
        bucket_field=None
        if query.bucket:
            bucket_field=query.bucket.output_field or f"__riskiq_bucket_{query.bucket.field}"
            filtered=filtered.copy()
            filtered[bucket_field]=self._bucket(filtered[query.bucket.field],query.bucket.ranges)
        dimensions=[d.field for d in query.dimensions]
        if bucket_field and bucket_field not in dimensions: dimensions.append(bucket_field)
        if not dimensions:
            rows=[self._measures(filtered,query)]
        else:
            rows=[]
            for keys,group in filtered.groupby(dimensions,dropna=False,sort=False,observed=True):
                if not isinstance(keys,tuple): keys=(keys,)
                row={field:self._json(v) for field,v in zip(dimensions,keys)}
                row.update(self._measures(group,query)); rows.append(row)
        return AnalystResult(dataset_id=query.dataset_id,dimensions=dimensions,measures=[m.name for m in query.measures],rows=rows,row_count=len(rows),metadata={"input_rows":len(dataset),"filtered_rows":len(filtered),"execution_engine":"pandas","declarative":True,"arbitrary_code_execution":False,"bucket_field":bucket_field})

    def _validate(self,q,frame):
        required={d.field for d in q.dimensions}|{f.field for f in q.filters}
        if q.bucket: required.add(q.bucket.field)
        for m in q.measures:
            if m.field: required.add(m.field)
            if m.name in {"exposure","par30","npl"}: required.add("outstanding_principal")
            if m.name in {"par30","npl"}: required.add("dpd")
            if m.name=="loan_count": required.add("loan_id")
            get_measure(m.name)
        missing=sorted(x for x in required if x not in frame.columns)
        if missing: raise ValueError(f"dataset is missing required columns: {', '.join(missing)}")

    def _filters(self,frame,filters:list[AnalystFilter]):
        mask=pd.Series(True,index=frame.index)
        for f in filters: mask &= self._filter(frame[f.field],f.operator,f.value)
        return frame.loc[mask] if filters else frame

    @staticmethod
    def _filter(s,op,v):
        if op=="eq": return s.eq(v)
        if op=="neq": return s.ne(v)
        if op in {"gt","gte","lt","lte"}:
            n=pd.to_numeric(s,errors="coerce"); x=float(v)
            return {"gt":n.gt,"gte":n.ge,"lt":n.lt,"lte":n.le}[op](x)
        if op in {"in","not_in"}:
            if not isinstance(v,(list,tuple,set)): raise ValueError(f"operator '{op}' requires a list")
            r=s.isin(list(v)); return ~r if op=="not_in" else r
        if op=="contains": return s.astype("string").str.contains(str(v),case=False,regex=False,na=False)
        raise ValueError(f"unsupported filter operator '{op}'")

    @staticmethod
    def _bucket(s,ranges):
        n=pd.to_numeric(s,errors="coerce")
        conditions=[]; labels=[]
        for r in ranges:
            c=n.ge(r.min) if r.max is None else n.ge(r.min)&n.lt(r.max)
            conditions.append(c.to_numpy()); labels.append(r.label)
        matrix=np.column_stack(conditions); codes=np.full(len(n),-1,dtype=np.int16)
        for i in range(matrix.shape[1]):
            assign=matrix[:,i]&(codes==-1); codes[assign]=i
        matched=matrix.any(axis=1)
        out=pd.Series(pd.Categorical.from_codes(codes,categories=labels),index=s.index)
        return out.where(matched,pd.NA)

    @staticmethod
    def _measures(frame,q):
        return {m.name:round(float(get_measure(m.name).compute(frame)),8) for m in q.measures}

    @staticmethod
    def _json(v):
        if pd.isna(v): return None
        if isinstance(v,np.integer): return int(v)
        if isinstance(v,np.floating): return float(v)
        if isinstance(v,np.bool_): return bool(v)
        return v
