import os
from pathlib import Path
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional
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
    """Returns real-time GCP instance scheduler shutdown status in Indian Standard Time (IST)."""
    from datetime import datetime, timezone, timedelta
    
    IST = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(IST)
    
    hours = now_ist.hour
    minutes = now_ist.minute
    seconds = now_ist.second
    
    is_countdown = (hours == 22 and minutes >= 30)
    is_offline = (hours >= 23 or hours < 6)
    
    seconds_remaining = 0
    if is_countdown:
        seconds_remaining = ((59 - minutes) * 60) + (60 - seconds)
        
    return {
        "timezone": "IST (UTC+05:30)",
        "current_ist_time": now_ist.strftime("%Y-%m-%d %H:%M:%S"),
        "is_countdown_active": is_countdown,
        "is_maintenance_window": is_offline,
        "seconds_until_shutdown": seconds_remaining,
        "shutdown_time": "23:00:00 IST (11:00 PM)",
        "startup_time": "06:00:00 IST (06:00 AM)",
        "gcp_scheduler_policy": "Daily auto-shutdown at 23:00 IST, auto-startup at 06:00 IST to optimize cloud costs"
    }

@router.get("/questions")
async def get_questions(
    category: Optional[str] = "All",
    search: Optional[str] = "",
    sort_by: Optional[str] = "recent"
):
    data = question_bank_service.get_data()
    companies = data["companies"]

    # Filter by category
    if category and category.lower() != "all":
        filtered = []
        for comp in companies:
            matching_rounds = []
            for r in comp["rounds"]:
                matching_qs = [q for q in r["questions"] if q["category"].lower() == category.lower()]
                if matching_qs:
                    r_copy = dict(r)
                    r_copy["questions"] = matching_qs
                    matching_rounds.append(r_copy)
            if matching_rounds:
                c_copy = dict(comp)
                c_copy["rounds"] = matching_rounds
                c_copy["total_questions"] = sum(len(r["questions"]) for r in matching_rounds)
                filtered.append(c_copy)
        companies = filtered

    # Filter by search
    if search:
        s = search.lower().strip()
        search_filtered = []
        for comp in companies:
            comp_match = s in comp["company_name"].lower()
            matching_rounds = []
            for r in comp["rounds"]:
                round_match = s in r["round_name"].lower()
                matching_qs = []
                for q in r["questions"]:
                    if (
                        comp_match or
                        round_match or
                        s in q["question"].lower() or
                        s in q["answer"].lower() or
                        s in q["category"].lower()
                    ):
                        matching_qs.append(q)
                if matching_qs:
                    r_copy = dict(r)
                    r_copy["questions"] = matching_qs
                    matching_rounds.append(r_copy)
            if matching_rounds:
                c_copy = dict(comp)
                c_copy["rounds"] = matching_rounds
                c_copy["total_questions"] = sum(len(r["questions"]) for r in matching_rounds)
                search_filtered.append(c_copy)
        companies = search_filtered

    # Sorting
    if sort_by == "name_asc":
        companies.sort(key=lambda c: c["company_name"].lower())
    elif sort_by == "name_desc":
        companies.sort(key=lambda c: c["company_name"].lower(), reverse=True)
    elif sort_by == "most_questions":
        companies.sort(key=lambda c: c["total_questions"], reverse=True)
    elif sort_by == "date":
        companies.sort(key=lambda c: c.get("timestamp", 0.0), reverse=True)
    else:  # recent
        companies.sort(key=lambda c: (c.get("file_order", 0.0), c.get("timestamp", 0.0), c["company_name"].lower()), reverse=True)

    return {
        "companies": companies,
        "count": len(companies),
        "total_questions": sum(c["total_questions"] for c in companies),
        "stats": data["stats"]
    }

@router.get("/calendar")
async def get_calendar_events():
    data = question_bank_service.get_data()
    return data["calendar_events"]

@router.get("/training/trees")
async def get_combined_training_trees():
    return training_service.get_combined_trees()

@router.get("/training/search")
async def search_training_files(q: str = Query(..., min_length=2), repo: Optional[str] = None):
    return training_service.search_files(q, repo)

@router.get("/training/tree/{repo_id}")
async def get_training_tree(repo_id: str):
    return training_service.get_repo_tree(repo_id)

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
    return sync_service.sync_repository(repo_id)

@router.post("/sync-all")
async def trigger_sync_all():
    return sync_service.sync_all()

@router.get("/logs")
async def get_logs(limit: int = 50):
    return {
        "logs": git_storage_service.get_audit_logs(limit),
        "status": git_storage_service.get_status()
    }
