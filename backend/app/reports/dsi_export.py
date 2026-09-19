from __future__ import annotations
import hashlib,hmac,json
from datetime import datetime,timezone
from io import BytesIO
from typing import Any
from app.config import settings
from app.data.mongo import MongoRepository
from app.data.persistence import PortfolioPersistenceService
from app.services.risk_intelligence_provider import RiskIntelligenceProvider
from app.stress_testing.stress_engine import StressEngine
def canonical_json(value: Any)->str:return json.dumps(value,sort_keys=True,separators=(",",":"),default=str)
def evidence_hash(payload: dict[str,Any])->str:return hashlib.sha256(canonical_json(payload).encode()).hexdigest()
class DSIReportService:
    VERSION="dsi-v1"
    def __init__(self):self.persistence=PortfolioPersistenceService();self.intelligence=RiskIntelligenceProvider();self.stress=StressEngine();self.repository=MongoRepository("dsi_reports")
    async def export(self,payload:dict[str,Any])->dict[str,Any]:
        dataset_id=str(payload.get("dataset_id") or "").strip()
        if not dataset_id:raise ValueError("dataset_id is required")
        snapshot_id=payload.get("snapshot_id");rows=payload.get("rows")
        if rows is not None and not isinstance(rows,list):raise ValueError("rows must be a list")
        if rows is None:rows=self.persistence.portfolio_records.find({"dataset_id":dataset_id},limit=500000)
        if not rows:raise ValueError("Dataset has no portfolio records")
        intelligence=await self.intelligence.build(dataset_id,rows=rows,snapshot_id=snapshot_id);intelligence.pop("evidence_hash",None)
        stress=payload.get("stress") or self.stress.run(intelligence["stress_testing"]["baseline"],str(payload.get("scenario") or "BASE"),payload.get("shocks"),payload.get("sensitivities"),payload.get("profile"))
        evidence={"dataset_id":dataset_id,"snapshot_id":snapshot_id or intelligence.get("snapshot_id"),"engine_version":self.VERSION,"raw_snapshot":rows,"risk_intelligence":intelligence,"stress":stress,"active_actions":payload.get("active_actions") or intelligence.get("risk_events",{}).get("actions",[])}
        digest=evidence_hash(evidence);signature=self._sign(digest)
        report={"contract_version":self.VERSION,"dataset_id":dataset_id,"snapshot_id":evidence["snapshot_id"],"generated_at":datetime.now(timezone.utc).isoformat(),"engine_version":self.VERSION,"evidence_hash":digest,"audit_signature":signature,"signature_algorithm":"HMAC-SHA256" if signature else "UNSIGNED","tamper_protection":"sha256-canonical-json","evidence_payload":evidence}
        self.repository.insert(report);return report
    def verify(self,digest:str)->dict[str,Any]:
        rows=self.repository.find({"evidence_hash":digest},limit=1)
        if not rows:return {"verified":False,"reason":"report_not_found","evidence_hash":digest}
        report=rows[0];calculated=evidence_hash(report["evidence_payload"]);sig=self._verify_signature(calculated,report.get("audit_signature"))
        return {"verified":hmac.compare_digest(calculated,digest),"evidence_hash":digest,"recalculated_hash":calculated,"signature_valid":sig,"tamper_detected":calculated!=digest,"generated_at":report.get("generated_at"),"dataset_id":report.get("dataset_id"),"contract_version":report.get("contract_version")}
    def pdf_bytes(self,report:dict[str,Any])->bytes:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        b=BytesIO();doc=SimpleDocTemplate(b,pagesize=A4);styles=getSampleStyleSheet();story=[Paragraph("RiskIQ — Data Integrity & Supervisory Evidence Report",styles["Title"]),Spacer(1,12)]
        for key in ("dataset_id","snapshot_id","generated_at","engine_version","evidence_hash","audit_signature","signature_algorithm"):story += [Paragraph(f"<b>{key}</b>: {report.get(key)}",styles["BodyText"]),Spacer(1,6)]
        story.append(Paragraph("Evidence is hashed using canonical JSON and contains the raw snapshot plus deterministic evidence required for reproducibility.",styles["BodyText"]));doc.build(story);return b.getvalue()
    @staticmethod
    def _sign(digest:str)->str|None:
        secret=settings.dsi_audit_signing_secret
        return hmac.new(secret.encode(),digest.encode(),hashlib.sha256).hexdigest() if secret else None
    @staticmethod
    def _verify_signature(digest:str,signature:str|None)->bool|None:
        secret=settings.dsi_audit_signing_secret
        if not secret or not signature:return None
        return hmac.compare_digest(hmac.new(secret.encode(),digest.encode(),hashlib.sha256).hexdigest(),signature)
