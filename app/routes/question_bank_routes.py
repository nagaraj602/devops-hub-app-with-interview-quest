from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional
from app.services.question_bank_service import question_bank_service
from app.services.page_visibility_service import page_visibility_service
from app.routes.admin_routes import is_admin_request, is_admin_server_request, admin_portal_view
from app.config import DEFAULT_REPOS

router = APIRouter()

_cached_default_html: Optional[str] = None

def invalidate_qb_html_cache():
    global _cached_default_html
    _cached_default_html = None

question_bank_service.add_on_refresh_callback(invalidate_qb_html_cache)
page_visibility_service.add_on_change_callback(invalidate_qb_html_cache)

@router.get("/", response_class=HTMLResponse)
@router.get("/question-bank", response_class=HTMLResponse)
async def question_bank_view(request: Request, category: Optional[str] = "All", search: Optional[str] = ""):
    # 1. On dedicated admin port (9256) / admin domain, '/' loads the Admin Dashboard directly
    if request.url.path == "/" and is_admin_server_request(request):
        return await admin_portal_view(request)
    # Check if Question Bank is currently published
    if not page_visibility_service.is_page_published("question_bank") and not is_admin_request(request):
        if request.url.path == "/":
            return RedirectResponse(url=page_visibility_service.get_first_published_route(), status_code=302)
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="page_unpublished.html",
            context={
                "page_title": "Section Hidden",
                "page_name": "Question Bank",
                "page_icon": "fa-circle-question",
                "active_page": "question_bank",
                "message": "The Question Bank section is currently unpublished by the administrator."
            },
            status_code=403
        )

    global _cached_default_html
    is_default = (category in (None, "All", "")) and (not search or not search.strip())

    if is_default and _cached_default_html is not None:
        return HTMLResponse(content=_cached_default_html)

    data = question_bank_service.get_data()
    template_response = request.app.state.templates.TemplateResponse(
        request=request,
        name="question_bank.html",
        context={
            "page_title": "Question Bank",
            "active_page": "question_bank",
            "companies": data["companies"],
            "stats": data["stats"],
            "category_pills": data["category_pills"],
            "calendar_events": data["calendar_events"],
            "selected_category": category,
            "search_query": search
        }
    )

    if is_default:
        _cached_default_html = template_response.body.decode("utf-8")

    return template_response
