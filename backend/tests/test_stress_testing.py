from app.stress_testing.stress_engine import StressEngine

def test_same_inputs_are_idempotent():
    baseline={"par30":0.10,"par60":0.05,"par90":0.03,"npl":0.02,"expected_loss":1000}
    sensitivity={"par30":{"unemployment":{"validated":True,"coefficient":0.7,"p_value":0.01,"sample_size":24,"elasticity":0.5}}}
    engine=StressEngine()
    a=engine.run(baseline,"ADVERSE",sensitivities=sensitivity)
    b=engine.run(baseline,"ADVERSE",sensitivities=sensitivity)
    assert a==b
    assert a["projected"]["par30"]>baseline["par30"]

def test_unvalidated_correlation_does_not_project():
    baseline={"par30":0.10}
    sensitivity={"par30":{"nasdaq_nq":{"validated":False,"coefficient":0.9,"p_value":0.01,"sample_size":24,"elasticity":1.0}}}
    result=StressEngine().run(baseline,"SEVERE_STRESS",sensitivities=sensitivity)
    assert result["projected"]["par30"]==baseline["par30"]
    assert result["evidence"]==[]
