import asyncio
import time
from app.services.risk_intelligence_provider import RiskIntelligenceProvider

def test_risk_intelligence_warm_cache_fast(monkeypatch):
    provider=RiskIntelligenceProvider()
    rows=[{"loan_id":"1","snapshot_date":"2026-09-01","dpd":30,"duration":10,"default":0}]
    monkeypatch.setattr(provider.persistence.datasets,"find",lambda *args,**kwargs:[{"dataset_id":"d1","updated_at":"v1"}])
    monkeypatch.setattr(provider.persistence.portfolio_records,"find",lambda *args,**kwargs:rows)
    monkeypatch.setattr(provider.analytics,"analyze",lambda rows:{"exposure":100,"par":{"par30":{"ratio":0.1},"par60":{"ratio":0.05},"par90":{"ratio":0.02}}})
    async def market():return {"status":"available","market_indicators":[],"macro_events":[]}
    monkeypatch.setattr(provider.market,"get_context",market)
    monkeypatch.setattr(provider.events,"list",lambda **kwargs:[]);monkeypatch.setattr(provider.actions,"list",lambda **kwargs:[])
    async def run():
        await provider.build("d1")
        start=time.perf_counter();result=await provider.build("d1");elapsed=(time.perf_counter()-start)*1000
        assert result["cache"]=="hit";assert elapsed<500
    asyncio.run(run())
