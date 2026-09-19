from fastapi import APIRouter,HTTPException
from fastapi.responses import Response
from .dsi_export import DSIReportService
router=APIRouter(prefix="/v1/reports",tags=["reports"]);service=DSIReportService()
@router.post("/dsi-export")
async def dsi_export(payload:dict):
    try:report=await service.export(payload)
    except (ValueError,TypeError) as exc:raise HTTPException(422,str(exc)) from exc
    if str(payload.get("format") or "json").lower()=="pdf":return Response(service.pdf_bytes(report),media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="riskiq-dsi-{report["evidence_hash"][:12]}.pdf"'})
    return report
@router.get("/verify/{digest}")
def verify_dsi(digest:str):return service.verify(digest)
