import asyncio
from app.reports.dsi_export import DSIReportService,evidence_hash
def test_dsi_hash_is_deterministic():
 p={"dataset_id":"d1","raw_snapshot":[{"loan_id":"1","dpd":30}],"risk":{"par30":0.2}}
 assert evidence_hash(p)==evidence_hash(p)
def test_dsi_report_builds_without_external_ai(monkeypatch):
 s=DSIReportService()
 async def fake_build(dataset_id,rows=None,snapshot_id=None):return {"dataset_id":dataset_id,"snapshot_id":snapshot_id,"stress_testing":{"baseline":{"par30":0.2}},"risk_events":{"actions":[]}}
 monkeypatch.setattr(s.intelligence,"build",fake_build);monkeypatch.setattr(s.repository,"insert",lambda doc:"r1")
 r=asyncio.run(s.export({"dataset_id":"d1","rows":[{"loan_id":"1","dpd":30}]}));assert len(r["evidence_hash"])==64
