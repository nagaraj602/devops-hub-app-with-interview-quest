from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.services.sync_service import sync_service
from app.services.git_storage_service import git_storage_service
from app.services.page_visibility_service import page_visibility_service
from app.routes.admin_routes import is_admin_request

router = APIRouter()

@router.get("/app-logs", response_class=HTMLResponse)
@router.get("/sync-all", response_class=HTMLResponse)
async def app_logs_view(request: Request):
    if request.url.path.startswith("/app-logs") and not page_visibility_service.is_page_published("app_logs") and not is_admin_request(request):
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="page_unpublished.html",
            context={
                "page_title": "Section Hidden",
                "page_name": "App Logs",
                "page_icon": "fa-server",
                "active_page": "app_logs",
                "message": "The App Logs section is currently unpublished by the administrator."
            },
            status_code=403
        )
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
