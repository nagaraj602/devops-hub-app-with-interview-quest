import os
from pathlib import Path
from fastapi import APIRouter, Query, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional, List
from app.services.question_bank_service import question_bank_service
from app.services.training_service import training_service
from app.services.cheatsheet_service import cheatsheet_service
from app.services.sync_service import sync_service
from app.services.git_storage_service import git_storage_service
from app.config import TRAINING_MATERIALS_DIR, NOTES_DIR

router = APIRouter(prefix="/api")

@router.get("/health")
async def health_check():
    """Health check endpoint for Docker Desktop K8s probes and deploy.sh verification."""
    return {
        "status": "healthy",
        "service": "devops-hub-portal",
        "port": 8926,
        "database": "git-native (https://github.com/nagaraj602/devops-hub-app-with-interview-quest.git)"
    }

@router.get("/maintenance-status")
async def get_maintenance_status():
    """Returns real-time cost optimization shutdown status in Indian Standard Time (IST)."""
    from datetime import datetime, timezone, timedelta
    
    IST = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(IST)
    
    hours = now_ist.hour
    minutes = now_ist.minute
    seconds = now_ist.second
    
    is_countdown = (hours == 23 and minutes >= 30)
    is_offline = (hours < 5 or (hours == 5 and minutes < 30))
    
    seconds_remaining = 0
    if is_countdown:
        seconds_remaining = ((59 - minutes) * 60) + (60 - seconds)
        
    return {
        "timezone": "IST (UTC+05:30)",
        "current_ist_time": now_ist.strftime("%Y-%m-%d %H:%M:%S"),
        "is_countdown_active": is_countdown,
        "is_offline_window": is_offline,
        "seconds_until_shutdown": seconds_remaining,
        "shutdown_time": "00:00:00 IST (12:00 AM)",
        "startup_time": "05:30:00 IST (05:30 AM)",
        "message": "This website is getting shutdown for cost optimization (12:00 AM to 5:30 AM). So it will come back at 5:30 am."
    }

@router.get("/questions")
async def get_questions(
    category: Optional[str] = "All",
    search: Optional[str] = "",
    sort_by: Optional[str] = "recent"
):
    companies = question_bank_service.filter_companies(category=category, search=search, sort_by=sort_by)
    data = question_bank_service.get_data()

    return {
        "companies": companies,
        "count": len(companies),
        "total_questions": sum(c.get("total_questions", 0) for c in companies),
        "stats": data["stats"]
    }

@router.get("/question-bank/chunk")
@router.get("/companies/chunk")
async def get_question_bank_chunk(
    request: Request,
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    category: Optional[str] = "All",
    search: Optional[str] = "",
    sort_by: Optional[str] = "recent",
    favorites: Optional[str] = "",
    is_companies_expanded: Optional[bool] = Query(None),
    is_answers_expanded: Optional[bool] = False,
    target_company: Optional[str] = None
):
    fav_list = [f.strip() for f in favorites.split(",") if f.strip()] if favorites else None
    filtered = question_bank_service.filter_companies(
        category=category,
        search=search,
        sort_by=sort_by,
        favorites=fav_list,
        target_company=target_company
    )

    total_matched = len(filtered)
    chunk = filtered[offset : offset + limit]
    has_more = (offset + len(chunk)) < total_matched

    # Auto-expand company/round accordions if category/search active, unless explicitly specified by client
    is_filtering = bool((category and category.strip().lower() not in ("all", "")) or (search and search.strip()))
    if is_companies_expanded is not None:
        auto_expand_companies = bool(is_companies_expanded)
    else:
        auto_expand_companies = bool(is_filtering)

    template = request.app.state.templates.get_template("partials/company_cards.html")
    html_content = template.render({
        "request": request,
        "companies": chunk,
        "start_index": offset + 1,
        "is_companies_expanded": auto_expand_companies,
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

@router.get("/calendar")
async def get_calendar_events():
    data = question_bank_service.get_data()
    return data["calendar_events"]

@router.get("/training/trees")
async def get_combined_training_trees(refresh: bool = False):
    return training_service.get_combined_trees(force_refresh=refresh)

@router.get("/training/search")
async def search_training_files(q: str = Query(..., min_length=2), repo: Optional[str] = None):
    return training_service.search_files(q, repo)

@router.get("/training/tree/{repo_id}")
async def get_training_tree(repo_id: str, refresh: bool = False):
    return training_service.get_repo_tree(repo_id, force_refresh=refresh)

@router.get("/training/file")
async def get_training_file(repo_id: str, path: str):
    return training_service.get_file_content(repo_id, path)

@router.get("/training/raw/{repo_id}/{file_path:path}")
async def get_raw_file(repo_id: str, file_path: str):
    base_dir = Path(TRAINING_MATERIALS_DIR) if repo_id == "training" else Path(NOTES_DIR)
    full_path = (base_dir / file_path).resolve()
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(full_path)

@router.get("/training/custom-repo")
async def fetch_custom_repo(repo_url: str, branch: Optional[str] = "main", file_path: Optional[str] = "README.md"):
    return training_service.fetch_live_github_content(repo_url, branch, file_path)

@router.get("/training/custom-tree")
async def fetch_custom_tree(repo_url: str, branch: Optional[str] = None):
    return training_service.fetch_github_repo_tree(repo_url, branch)

@router.get("/cheatsheet")
async def get_cheatsheet(category: Optional[str] = "all", search: Optional[str] = ""):
    data = cheatsheet_service.get_data()
    items = data["all_items"]

    if category and category.lower() != "all":
        items = [i for i in items if i["category_id"].lower() == category.lower()]

    if search:
        s = search.lower().strip()
        items = [
            i for i in items
            if s in i.get("command", "").lower() or
               s in i.get("explanation", "").lower() or
               s in i.get("section", "").lower() or
               any(s in t.lower() for t in i.get("tags", []))
        ]

    return {"items": items, "count": len(items)}

@router.post("/sync/{repo_id}")
async def trigger_sync(repo_id: str):
    res = sync_service.sync_repository(repo_id)
    try:
        from app.routes.sync_routes import invalidate_sync_views_cache
        invalidate_sync_views_cache()
    except Exception:
        pass
    return res

@router.post("/sync-all")
async def trigger_sync_all():
    res = sync_service.sync_all()
    try:
        from app.routes.sync_routes import invalidate_sync_views_cache
        invalidate_sync_views_cache()
    except Exception:
        pass
    return res

@router.get("/logs")
async def get_logs(limit: int = 50):
    return {
        "logs": git_storage_service.get_audit_logs(limit),
        "status": git_storage_service.get_status()
    }
