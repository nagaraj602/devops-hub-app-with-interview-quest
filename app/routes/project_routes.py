from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.services.project_service import project_service

router = APIRouter()

@router.get("/project", response_class=HTMLResponse)
async def project_view(request: Request):
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
