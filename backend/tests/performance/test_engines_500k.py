from __future__ import annotations
import time,tracemalloc
import pytest
from app.predictive.transition_engine import TransitionEngine
from app.predictive.survival_engine import SurvivalEngine
pytestmark=pytest.mark.performance
@pytest.fixture(scope="module")
def rows_500k():
 return [{"loan_id":str(loan),"snapshot_date":f"2026-{snap+1:02d}-01","dpd":(loan+snap*13)%120,"duration":(loan%360)+snap,"default":int((loan+snap)%17==0)} for loan in range(100000) for snap in range(5)]
def measure(fn,rows):
 tracemalloc.start();t=time.perf_counter();result=fn(rows);ms=(time.perf_counter()-t)*1000;_,peak=tracemalloc.get_traced_memory();tracemalloc.stop();return result,ms,peak/(1024*1024)
def test_transition_500k(rows_500k):
 r,ms,ram=measure(TransitionEngine().build_matrix,rows_500k);assert r.sample_size==400000;print(f"TRANSITION_500K_MS={ms:.2f} RAM_MB={ram:.2f}")
def test_survival_500k(rows_500k):
 r,ms,ram=measure(SurvivalEngine().kaplan_meier,rows_500k);assert r.sample_size==500000;print(f"SURVIVAL_500K_MS={ms:.2f} RAM_MB={ram:.2f}")
