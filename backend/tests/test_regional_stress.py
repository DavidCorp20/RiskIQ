from app.stress_testing.stress_engine import StressEngine
def test_guardrail_blocks_unvalidated():
 r=StressEngine().run({"par30":0.2},"ADVERSE",profile="LATAM_SEVERE_INFLATION",sensitivities={"par30":{"inflation":{"validated":False,"coefficient":0.9,"p_value":0.01,"sample_size":100,"elasticity":1.0}}})
 assert r["projected"]["par30"]==0.2 and r["evidence"]==[]
def test_guardrail_allows_validated():
 r=StressEngine().run({"par30":0.2},"ADVERSE",profile="LATAM_CONSERVATIVE",sensitivities={"par30":{"inflation":{"validated":True,"coefficient":0.7,"p_value":0.01,"sample_size":24,"elasticity":1.0}}})
 assert r["projected"]["par30"]>0.2 and r["evidence"][0]["classification"]=="CORRELATED"
