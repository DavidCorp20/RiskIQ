import asyncio
from app.services.risk_intelligence_provider import RiskIntelligenceProvider

def test_provider_contract(monkeypatch):
    provider=RiskIntelligenceProvider()
    rows=[{"loan_id":"1","snapshot_date":"2026-01-01","dpd":0,"outstanding_principal":100},{"loan_id":"1","snapshot_date":"2026-02-01","dpd":30,"outstanding_principal":90}]
    class Repo:
        def find(self,*args,**kwargs): return rows
    provider.persistence.portfolio_records=Repo()
    class Empty:
        def list(self,*args,**kwargs): return []
    provider.events=Empty(); provider.actions=Empty()
    class Market:
        async def get_context(self): return {"status":"unavailable","market_indicators":{},"macro_events":[]}
    provider.market=Market()
    result=asyncio.run(provider.build("ds"))
    assert result["ai_mutable_fields"]==[]
    assert result["deterministic"] is True
    assert result["evidence_hash"]
