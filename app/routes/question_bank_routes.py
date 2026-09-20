from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from typing import Optional
from app.services.question_bank_service import question_bank_service
from app.config import DEFAULT_REPOS

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
@router.get("/question-bank", response_class=HTMLResponse)
async def question_bank_view(request: Request, category: Optional[str] = "All", search: Optional[str] = ""):
    data = question_bank_service.get_data()
    return request.app.state.templates.TemplateResponse(
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
