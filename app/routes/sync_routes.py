from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.services.sync_service import sync_service
from app.services.git_storage_service import git_storage_service

router = APIRouter()

@router.get("/sync-all", response_class=HTMLResponse)
async def sync_all_view(request: Request):
    sync_status = sync_service.get_sync_status()
    audit_logs = git_storage_service.get_audit_logs(limit=30)
    system_status = git_storage_service.get_status()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="sync.html",
        context={
            "page_title": "Sync All & Continuous Logs",
            "active_page": "sync",
            "sync_status": sync_status,
            "audit_logs": audit_logs,
            "system_status": system_status
        }
    )
