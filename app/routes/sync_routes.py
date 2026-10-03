import time
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from typing import Optional
from app.services.sync_service import sync_service
from app.services.git_storage_service import git_storage_service
from app.services.page_visibility_service import page_visibility_service
from app.routes.admin_routes import is_admin_request

router = APIRouter()

_cached_app_logs_html: Optional[str] = None
_cached_sync_html: Optional[str] = None
_cached_time: float = 0
CACHE_TTL = 30  # 30 seconds TTL for fast page navigation

def invalidate_sync_views_cache():
    global _cached_app_logs_html, _cached_sync_html, _cached_time
    _cached_app_logs_html = None
    _cached_sync_html = None
    _cached_time = 0

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

    global _cached_app_logs_html, _cached_sync_html, _cached_time
    now = time.time()
    is_app_logs = request.url.path.startswith("/app-logs")
    active_page = "app_logs" if is_app_logs else "sync"

    if (now - _cached_time) < CACHE_TTL:
        cached_content = _cached_app_logs_html if is_app_logs else _cached_sync_html
        if cached_content:
            return HTMLResponse(
                content=cached_content,
                headers={"Cache-Control": "private, max-age=10"}
            )

    sync_status = sync_service.get_sync_status()
    audit_logs = git_storage_service.get_audit_logs(limit=50)
    system_status = git_storage_service.get_status()
    runtime_info = git_storage_service.get_runtime_environment()

    template_response = request.app.state.templates.TemplateResponse(
        request=request,
        name="sync.html",
        context={
            "page_title": "App Logs & Active Component Health",
            "active_page": active_page,
            "sync_status": sync_status,
            "audit_logs": audit_logs,
            "system_status": system_status,
            "runtime_info": runtime_info
        },
        headers={"Cache-Control": "private, max-age=10"}
    )

    rendered_body = template_response.body.decode("utf-8")
    if is_app_logs:
        _cached_app_logs_html = rendered_body
    else:
        _cached_sync_html = rendered_body
    _cached_time = now

    return template_response
