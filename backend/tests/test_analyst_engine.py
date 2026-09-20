import pandas as pd
import pytest
from app.analytics.analyst_engine import AnalystEngine
from app.analytics.analyst_models import AnalystBucket,AnalystBucketRange,AnalystDimension,AnalystFilter,AnalystMeasure,AnalystQuery

@pytest.fixture
def portfolio():
    return pd.DataFrame([
        {"loan_id":"A","segment":"Micro","dpd":10,"outstanding_principal":100.0},
        {"loan_id":"B","segment":"Micro","dpd":45,"outstanding_principal":200.0},
        {"loan_id":"C","segment":"SME","dpd":75,"outstanding_principal":300.0},
        {"loan_id":"D","segment":"SME","dpd":120,"outstanding_principal":400.0},
    ])

def test_aggregate_measures(portfolio):
    q=AnalystQuery(dataset_id="demo",dimensions=[AnalystDimension(field="segment")],measures=[AnalystMeasure(name="exposure"),AnalystMeasure(name="loan_count"),AnalystMeasure(name="par30"),AnalystMeasure(name="npl")])
    rows=AnalystEngine().execute(q,portfolio).rows
    micro=next(r for r in rows if r["segment"]=="Micro")
    assert micro["exposure"]==300.0 and micro["loan_count"]==2.0
    assert micro["par30"]==round(200/300,8) and micro["npl"]==0.0

def test_dynamic_bucket(portfolio):
    q=AnalystQuery(dataset_id="demo",dimensions=[AnalystDimension(field="segment")],measures=[AnalystMeasure(name="exposure")],bucket=AnalystBucket(field="dpd",ranges=[AnalystBucketRange(min=0,max=30,label="0-29"),AnalystBucketRange(min=30,max=60,label="30-59"),AnalystBucketRange(min=60,max=90,label="60-89"),AnalystBucketRange(min=90,max=None,label="90+")]))
    result=AnalystEngine().execute(q,portfolio)
    assert "segment" in result.dimensions and sum(r["exposure"] for r in result.rows)==1000.0

def test_safe_filter(portfolio):
    q=AnalystQuery(dataset_id="demo",measures=[AnalystMeasure(name="exposure")],filters=[AnalystFilter(field="dpd",operator="gte",value=30)])
    result=AnalystEngine().execute(q,portfolio)
    assert result.metadata["arbitrary_code_execution"] is False and result.metadata["filtered_rows"]==3
    assert result.rows[0]["exposure"]==900.0

def test_missing_field(portfolio):
    q=AnalystQuery(dataset_id="demo",measures=[AnalystMeasure(name="par30")])
    with pytest.raises(ValueError,match="dpd"): AnalystEngine().execute(q,portfolio.drop(columns=["dpd"]))
