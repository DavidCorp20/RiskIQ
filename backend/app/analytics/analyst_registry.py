from __future__ import annotations
from abc import ABC, abstractmethod
import pandas as pd

class BaseMeasure(ABC):
    name: str
    label: str
    @abstractmethod
    def compute(self, frame: pd.DataFrame) -> float: raise NotImplementedError
    @staticmethod
    def number(frame: pd.DataFrame, field: str) -> pd.Series:
        if field not in frame.columns: raise KeyError(f"required field '{field}' is not available")
        return pd.to_numeric(frame[field], errors="coerce").fillna(0.0)

class ExposureMeasure(BaseMeasure):
    name="exposure"; label="Exposure"
    def compute(self, frame): return float(self.number(frame,"outstanding_principal").sum())

class LoanCountMeasure(BaseMeasure):
    name="loan_count"; label="Loan count"
    def compute(self, frame):
        if "loan_id" not in frame.columns: raise KeyError("required field 'loan_id' is not available")
        return float(frame["loan_id"].dropna().nunique())

class PAR30Measure(BaseMeasure):
    name="par30"; label="PAR30"
    def compute(self, frame):
        exposure=self.number(frame,"outstanding_principal"); dpd=self.number(frame,"dpd")
        total=float(exposure.sum())
        return float(exposure.where(dpd>=30,0.0).sum())/total if total else 0.0

class NPLMeasure(BaseMeasure):
    name="npl"; label="NPL proxy"
    def compute(self, frame):
        exposure=self.number(frame,"outstanding_principal"); dpd=self.number(frame,"dpd")
        total=float(exposure.sum())
        return float(exposure.where(dpd>=90,0.0).sum())/total if total else 0.0

class BaseDimension(ABC):
    name: str
    def resolve(self, frame: pd.DataFrame, field: str) -> pd.Series:
        if field not in frame.columns: raise KeyError(f"dimension field '{field}' is not available")
        return frame[field]

class ColumnDimension(BaseDimension):
    name="column"

MEASURE_REGISTRY={m.name:m for m in [ExposureMeasure,LoanCountMeasure,PAR30Measure,NPLMeasure]}
DIMENSION_REGISTRY={"column":ColumnDimension}

def get_measure(name: str) -> BaseMeasure:
    try: return MEASURE_REGISTRY[name]()
    except KeyError as exc: raise ValueError(f"unsupported measure '{name}'. Available: {', '.join(sorted(MEASURE_REGISTRY))}") from exc

def get_dimension(name: str="column") -> BaseDimension:
    try: return DIMENSION_REGISTRY[name]()
    except KeyError as exc: raise ValueError(f"unsupported dimension type '{name}'") from exc
