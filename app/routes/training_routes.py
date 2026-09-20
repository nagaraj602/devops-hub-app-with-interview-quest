from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from app.services.training_service import training_service

router = APIRouter()

@router.get("/training-materials", response_class=HTMLResponse)
async def training_materials_view(request: Request, repo: str = "training"):
    tree = training_service.get_repo_tree(repo)
    initial_file = training_service.get_file_content(repo, "README.md")
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="training.html",
        context={
            "page_title": "Training Materials & Notes Explorer",
            "active_page": "training",
            "current_repo": repo,
            "tree": tree,
            "initial_file": initial_file
        }
    )
