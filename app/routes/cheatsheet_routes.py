from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from typing import Optional
from app.services.cheatsheet_service import cheatsheet_service

router = APIRouter()

@router.get("/command-cheatsheet", response_class=HTMLResponse)
async def command_cheatsheet_view(request: Request, category: Optional[str] = "all"):
    data = cheatsheet_service.get_data()
    return request.app.state.templates.TemplateResponse(
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
