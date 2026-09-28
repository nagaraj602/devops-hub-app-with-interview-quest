from typing import Optional
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from app.services.cheatsheet_service import cheatsheet_service
from app.services.page_visibility_service import page_visibility_service
from app.routes.admin_routes import is_admin_request

router = APIRouter()

_cached_cheatsheet_html: Optional[str] = None

def invalidate_cheatsheet_html_cache():
    global _cached_cheatsheet_html
    _cached_cheatsheet_html = None

page_visibility_service.add_on_change_callback(invalidate_cheatsheet_html_cache)

@router.get("/command-cheatsheet", response_class=HTMLResponse)
async def command_cheatsheet_view(request: Request, category: Optional[str] = "all"):
    if not page_visibility_service.is_page_published("cheatsheet") and not is_admin_request(request):
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="page_unpublished.html",
            context={
                "page_title": "Section Hidden",
                "page_name": "Command Cheatsheet",
                "page_icon": "fa-terminal",
                "active_page": "cheatsheet",
                "message": "The Command Cheatsheet section is currently unpublished by the administrator."
            },
            status_code=403
        )

    is_default = (category in (None, "all", ""))
    global _cached_cheatsheet_html
    if is_default and _cached_cheatsheet_html is not None and not is_admin_request(request):
        return HTMLResponse(content=_cached_cheatsheet_html)

    data = cheatsheet_service.get_data()
    template_response = request.app.state.templates.TemplateResponse(
        request=request,
        name="cheatsheet.html",
        context={
            "page_title": "Command Cheatsheet",
            "active_page": "cheatsheet",
            "categories": data["categories"],
            "category_details": data["category_details"],
            "all_items": data["all_items"],
            "selected_category": category,
            "total_commands": data["total_commands"]
        }
    )

    if is_default and not is_admin_request(request):
        _cached_cheatsheet_html = template_response.body.decode("utf-8")

    return template_response
