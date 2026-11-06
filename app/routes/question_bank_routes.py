from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse, Response, PlainTextResponse
from typing import Optional
import re
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
async def question_bank_view(
    request: Request,
    category: Optional[str] = "All",
    search: Optional[str] = "",
    sort_by: Optional[str] = "recent"
):
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
    is_default = (category in (None, "All", "")) and (not search or not search.strip()) and (sort_by in (None, "recent"))

    if is_default and _cached_default_html is not None:
        return HTMLResponse(
            content=_cached_default_html,
            headers={"Cache-Control": "private, max-age=120, stale-while-revalidate=300"}
        )

    data = question_bank_service.get_data()
    if is_default:
        all_companies = data["companies"]
        initial_companies = all_companies[:10]
        total_count = len(all_companies)
    else:
        filtered = question_bank_service.filter_companies(category=category, search=search, sort_by=sort_by)
        initial_companies = filtered[:10]
        total_count = len(filtered)

    template_response = request.app.state.templates.TemplateResponse(
        request=request,
        name="question_bank.html",
        context={
            "page_title": "Question Bank",
            "active_page": "question_bank",
            "companies": initial_companies,
            "total_companies_count": total_count,
            "stats": data["stats"],
            "category_pills": data["category_pills"],
            "calendar_events": data["calendar_events"],
            "selected_category": category,
            "search_query": search,
            "sort_by": sort_by,
            "is_group_by_company": (sort_by == "group_by_company"),
            "is_companies_expanded": not is_default
        },
        headers={"Cache-Control": "private, max-age=120, stale-while-revalidate=300"}
    )

    if is_default:
        _cached_default_html = template_response.body.decode("utf-8")

    return template_response

@router.get("/api/question-bank/download-round")
async def download_qb_round(
    round_id: Optional[str] = Query(None, description="ID of the round to download"),
    company_name: Optional[str] = Query(None, description="Company name"),
    round_name: Optional[str] = Query(None, description="Round name"),
    format: Optional[str] = Query("pdf", description="File format: pdf, md, html, or txt")
):
    round_info = question_bank_service.get_round(
        round_id=round_id,
        company_name=company_name,
        round_name=round_name
    )
    if not round_info:
        return PlainTextResponse("Round not found", status_code=404)

    comp_name = round_info.get("company_name", "Company")
    r_name = round_info.get("round_name", "Round")

    safe_comp = re.sub(r'[^a-zA-Z0-9_\-]', '_', comp_name).strip('_')
    safe_round = re.sub(r'[^a-zA-Z0-9_\-]', '_', r_name).strip('_')
    base_name = f"{safe_comp}_{safe_round}_Questions"

    fmt = (format or "pdf").lower().strip()

    if fmt == "html" or fmt == "preview":
        html_str = question_bank_service.generate_round_html(round_info)
        return HTMLResponse(content=html_str)

    if fmt == "md":
        content = question_bank_service.generate_round_markdown(round_info)
        headers = {
            "Content-Disposition": f'attachment; filename="{base_name}.md"',
            "Content-Type": "text/markdown; charset=utf-8"
        }
        return Response(content=content, media_type="text/markdown; charset=utf-8", headers=headers)

    if fmt == "txt":
        content = question_bank_service.generate_round_markdown(round_info)
        headers = {
            "Content-Disposition": f'attachment; filename="{base_name}.txt"',
            "Content-Type": "text/plain; charset=utf-8"
        }
        return Response(content=content, media_type="text/plain; charset=utf-8", headers=headers)

    # Default: PDF
    pdf_bytes = question_bank_service.generate_round_pdf(round_info)
    headers = {
        "Content-Disposition": f'attachment; filename="{base_name}.pdf"',
        "Content-Type": "application/pdf"
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

@router.get("/api/question-bank/download-company")
async def download_qb_company(
    company_name: str = Query(..., description="Company name to download"),
    format: Optional[str] = Query("pdf", description="File format: pdf, md, html, or txt")
):
    company = question_bank_service.get_company(company_name)
    if not company:
        return PlainTextResponse("Company not found", status_code=404)

    comp_name = company.get("company_name", "Company")
    safe_comp = re.sub(r'[^a-zA-Z0-9_\-]', '_', comp_name).strip('_')
    base_name = f"{safe_comp}_All_Interview_Questions"

    fmt = (format or "pdf").lower().strip()

    if fmt == "html" or fmt == "preview":
        html_str = question_bank_service.generate_company_html(company)
        return HTMLResponse(content=html_str)

    if fmt == "md":
        content = question_bank_service.generate_company_markdown(company)
        headers = {
            "Content-Disposition": f'attachment; filename="{base_name}.md"',
            "Content-Type": "text/markdown; charset=utf-8"
        }
        return Response(content=content, media_type="text/markdown; charset=utf-8", headers=headers)

    # Default: PDF
    pdf_bytes = question_bank_service.generate_company_pdf(company)
    headers = {
        "Content-Disposition": f'attachment; filename="{base_name}.pdf"',
        "Content-Type": "application/pdf"
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
