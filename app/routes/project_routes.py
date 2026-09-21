from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.services.project_service import project_service
from app.services.page_visibility_service import page_visibility_service
from app.routes.admin_routes import is_admin_request

router = APIRouter()

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

    data = project_service.get_project_data()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="project.html",
        context={
            "page_title": "Project Architecture & Guide",
            "active_page": "project",
            "project": data
        }
    )
