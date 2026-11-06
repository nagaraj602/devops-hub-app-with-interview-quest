from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse, Response, PlainTextResponse
from typing import Optional, List
import re
from app.services.qa_service import qa_service
from app.services.page_visibility_service import page_visibility_service
from app.routes.admin_routes import is_admin_request

router = APIRouter()

_cached_default_qa_html: Optional[str] = None

def invalidate_qa_html_cache():
    global _cached_default_qa_html
    _cached_default_qa_html = None

qa_service.add_on_refresh_callback(invalidate_qa_html_cache)
page_visibility_service.add_on_change_callback(invalidate_qa_html_cache)

@router.get("/qa-questions", response_class=HTMLResponse)
async def qa_questions_view(
    request: Request,
    instructor: Optional[str] = "All",
    search: Optional[str] = "",
    sort_by: Optional[str] = "recent"
):
    if not page_visibility_service.is_page_published("qa_questions") and not is_admin_request(request):
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="page_unpublished.html",
            context={
                "page_title": "Section Hidden",
                "page_name": "QA Questions",
                "page_icon": "fa-clipboard-question",
                "active_page": "qa_questions",
                "message": "The QA Questions section is currently unpublished by the administrator."
            },
            status_code=403
        )

    global _cached_default_qa_html
    is_default = (instructor in (None, "All", "")) and (not search or not search.strip()) and (sort_by in (None, "recent", "default"))

    if is_default and _cached_default_qa_html is not None:
        return HTMLResponse(
            content=_cached_default_qa_html,
            headers={"Cache-Control": "private, max-age=120, stale-while-revalidate=300"}
        )

    data = qa_service.get_data()
    all_instructors = data.get("instructors", [])

    if is_default:
        # Load first 2 instructors initially for fast page load on 2 CPU 8GB RAM laptops
        initial_chunk = all_instructors[:2]
        total_matched = len(all_instructors)
    else:
        filtered = qa_service.filter_qa(instructor=instructor, search=search, sort_by=sort_by)
        initial_chunk = filtered[:2]
        total_matched = len(filtered)

    template_response = request.app.state.templates.TemplateResponse(
        request=request,
        name="qa_questions.html",
        context={
            "request": request,
            "page_title": "QA Questions | DevOps Hub",
            "active_page": "qa_questions",
            "instructors": initial_chunk,
            "stats": data.get("stats", {}),
            "instructor_pills": data.get("instructor_pills", []),
            "selected_instructor": instructor or "All",
            "search_query": search or "",
            "sort_by": sort_by or "recent",
            "total_matched": total_matched,
            "has_more": len(initial_chunk) < total_matched,
            "is_sessions_expanded": False,
            "is_answers_expanded": False
        }
    )

    if is_default:
        try:
            _cached_default_qa_html = template_response.body.decode("utf-8")
        except Exception:
            pass

    return template_response

@router.get("/api/qa-questions/chunk")
async def get_qa_chunk(
    request: Request,
    offset: int = Query(0, ge=0),
    limit: int = Query(2, ge=1, le=20),
    instructor: Optional[str] = "All",
    search: Optional[str] = "",
    sort_by: Optional[str] = "recent",
    favorites: Optional[str] = "",
    is_sessions_expanded: Optional[bool] = Query(None),
    is_answers_expanded: Optional[bool] = False
):
    fav_list = [f.strip() for f in favorites.split(",") if f.strip()] if favorites else None
    filtered = qa_service.filter_qa(
        instructor=instructor,
        search=search,
        sort_by=sort_by,
        favorites=fav_list
    )

    total_matched = len(filtered)
    chunk = filtered[offset : offset + limit]
    has_more = (offset + len(chunk)) < total_matched

    is_filtering = bool((instructor and instructor.strip().lower() not in ("all", "")) or (search and search.strip()))
    if is_sessions_expanded is not None:
        auto_expand_sessions = bool(is_sessions_expanded)
    else:
        auto_expand_sessions = bool(is_filtering)

    template = request.app.state.templates.get_template("partials/qa_cards.html")
    html_content = template.render({
        "request": request,
        "instructors": chunk,
        "start_index": offset + 1,
        "sort_by": sort_by,
        "is_sessions_expanded": auto_expand_sessions,
        "is_answers_expanded": bool(is_answers_expanded)
    })

    return {
        "html": html_content,
        "offset": offset,
        "limit": limit,
        "count": len(chunk),
        "total_matched": total_matched,
        "has_more": has_more
    }

@router.get("/api/qa-questions/download")
async def download_qa_session(
    session_id: str = Query(..., description="ID of the session to download"),
    instructor_id: Optional[str] = Query(None, description="Optional instructor ID"),
    format: Optional[str] = Query("pdf", description="File format: pdf, md, html, or txt")
):
    session = qa_service.get_session(session_id, instructor_id=instructor_id)
    if not session:
        return PlainTextResponse("QA Session not found", status_code=404)

    inst_name = session.get("instructor_name", "Instructor")
    sess_name = session.get("session_name", session.get("date", "Session"))

    safe_inst = re.sub(r'[^a-zA-Z0-9_\-]', '_', inst_name).strip('_')
    safe_sess = re.sub(r'[^a-zA-Z0-9_\-]', '_', sess_name).strip('_')

    base_name = f"{safe_inst}_{safe_sess}" if "qa" in safe_sess.lower() else f"{safe_inst}_{safe_sess}_QA"
    fmt = (format or "pdf").lower().strip()

    if fmt == "html" or fmt == "preview":
        html_str = qa_service.generate_session_html(session)
        return HTMLResponse(content=html_str)

    if fmt == "md":
        content = qa_service.generate_session_markdown(session)
        headers = {
            "Content-Disposition": f'attachment; filename="{base_name}.md"',
            "Content-Type": "text/markdown; charset=utf-8"
        }
        return Response(content=content, media_type="text/markdown; charset=utf-8", headers=headers)

    if fmt == "txt":
        content = qa_service.generate_session_markdown(session)
        headers = {
            "Content-Disposition": f'attachment; filename="{base_name}.txt"',
            "Content-Type": "text/plain; charset=utf-8"
        }
        return Response(content=content, media_type="text/plain; charset=utf-8", headers=headers)

    # Default: PDF
    pdf_bytes = qa_service.generate_session_pdf(session)
    headers = {
        "Content-Disposition": f'attachment; filename="{base_name}.pdf"',
        "Content-Type": "application/pdf"
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

@router.get("/api/qa-questions/download-instructor")
async def download_qa_instructor(
    instructor_id: str = Query(..., description="ID of the instructor to download"),
    format: Optional[str] = Query("pdf", description="File format: pdf, md, html, or txt")
):
    instructor = qa_service.get_instructor(instructor_id)
    if not instructor:
        return PlainTextResponse("Instructor not found", status_code=404)

    inst_name = instructor.get("name", "Instructor")
    safe_inst = re.sub(r'[^a-zA-Z0-9_\-]', '_', inst_name).strip('_')
    fmt = (format or "pdf").lower().strip()

    if fmt == "html" or fmt == "preview":
        html_str = qa_service.generate_instructor_html(instructor)
        return HTMLResponse(content=html_str)

    if fmt == "md":
        content = qa_service.generate_instructor_markdown(instructor)
        headers = {
            "Content-Disposition": f'attachment; filename="{safe_inst}_All_QA_Questions.md"',
            "Content-Type": "text/markdown; charset=utf-8"
        }
        return Response(content=content, media_type="text/markdown; charset=utf-8", headers=headers)

    # Default: PDF
    pdf_bytes = qa_service.generate_instructor_pdf(instructor)
    headers = {
        "Content-Disposition": f'attachment; filename="{safe_inst}_All_QA_Questions.pdf"',
        "Content-Type": "application/pdf"
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
