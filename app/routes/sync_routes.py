from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.services.sync_service import sync_service
from app.services.git_storage_service import git_storage_service

router = APIRouter()

@router.get("/app-logs", response_class=HTMLResponse)
@router.get("/sync-all", response_class=HTMLResponse)
async def app_logs_view(request: Request):
    sync_status = sync_service.get_sync_status()
    audit_logs = git_storage_service.get_audit_logs(limit=50)
    system_status = git_storage_service.get_status()
    runtime_info = git_storage_service.get_runtime_environment()
    active_page = "app_logs" if request.url.path.startswith("/app-logs") else "sync"

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="sync.html",
        context={
            "page_title": "App Logs & Active Component Health",
            "active_page": active_page,
            "sync_status": sync_status,
            "audit_logs": audit_logs,
            "system_status": system_status,
            "runtime_info": runtime_info
        }
    )
