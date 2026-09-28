from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.services.project_service import project_service
from app.services.page_visibility_service import page_visibility_service
from app.routes.admin_routes import is_admin_request

router = APIRouter()

_cached_project_html: Optional[str] = None

def invalidate_project_html_cache():
    global _cached_project_html
    _cached_project_html = None

project_service.add_on_refresh_callback(invalidate_project_html_cache)
page_visibility_service.add_on_change_callback(invalidate_project_html_cache)

@router.get("/project", response_class=HTMLResponse)
async def project_view(request: Request):
    if not page_visibility_service.is_page_published("project") and not is_admin_request(request):
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="page_unpublished.html",
            context={
                "page_title": "Section Hidden",
                "page_name": "Project Architecture",
                "page_icon": "fa-diagram-project",
                "active_page": "project",
                "message": "The Project Architecture section is currently unpublished by the administrator."
            },
            status_code=403
        )

    global _cached_project_html
    if _cached_project_html is not None and not is_admin_request(request):
        return HTMLResponse(content=_cached_project_html)

    data = project_service.get_project_data()
    template_response = request.app.state.templates.TemplateResponse(
        request=request,
        name="project.html",
        context={
            "page_title": "Project Architecture & Guide",
            "active_page": "project",
            "project": data
        }
    )

    if not is_admin_request(request):
        _cached_project_html = template_response.body.decode("utf-8")

    return template_response
