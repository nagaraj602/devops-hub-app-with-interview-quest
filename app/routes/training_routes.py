from typing import Optional
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from app.services.training_service import training_service
from app.services.page_visibility_service import page_visibility_service
from app.routes.admin_routes import is_admin_request

router = APIRouter()

_cached_training_html: Optional[str] = None

def invalidate_training_html_cache():
    global _cached_training_html
    _cached_training_html = None

training_service.add_on_refresh_callback(invalidate_training_html_cache)
page_visibility_service.add_on_change_callback(invalidate_training_html_cache)

@router.get("/training-materials", response_class=HTMLResponse)
async def training_materials_view(request: Request, repo: str = "training"):
    if not page_visibility_service.is_page_published("training") and not is_admin_request(request):
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="page_unpublished.html",
            context={
                "page_title": "Section Hidden",
                "page_name": "Training Materials",
                "page_icon": "fa-book-open-reader",
                "active_page": "training",
                "message": "The Training Materials section is currently unpublished by the administrator."
            },
            status_code=403
        )

    is_default = (repo == "training")
    global _cached_training_html
    if is_default and _cached_training_html is not None and not is_admin_request(request):
        # Auto-invalidate if cached HTML was generated before training materials were populated
        if ("AWS" in _cached_training_html or "linux" in _cached_training_html or "jenkins" in _cached_training_html):
            return HTMLResponse(content=_cached_training_html)
        _cached_training_html = None

    trees = training_service.get_combined_trees()
    tree = training_service.get_repo_tree(repo)
    initial_file = training_service.get_file_content(repo, "README.md")
    template_response = request.app.state.templates.TemplateResponse(
        request=request,
        name="training.html",
        context={
            "page_title": "Training Materials & Notes Explorer",
            "active_page": "training",
            "current_repo": repo,
            "trees": trees,
            "tree": tree,
            "initial_file": initial_file
        }
    )

    if is_default and not is_admin_request(request):
        _cached_training_html = template_response.body.decode("utf-8")

    return template_response
