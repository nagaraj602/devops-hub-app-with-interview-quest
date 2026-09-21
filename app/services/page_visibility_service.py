import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from app.config import PAGE_VISIBILITY_FILE
from app.services.git_storage_service import git_storage_service

DEFAULT_PAGES: Dict[str, Dict[str, Any]] = {
    "question_bank": {
        "key": "question_bank",
        "name": "Question Bank",
        "route": "/question-bank",
        "is_published": True,
        "icon": "fa-circle-question",
        "description": "53 Curated Organizations & 1,291 Interview Questions categorized by technology and round."
    },
    "project": {
        "key": "project",
        "name": "Project Architecture",
        "route": "/project",
        "is_published": True,
        "icon": "fa-diagram-project",
        "description": "E-Commerce Marketplace Risk Detection Platform, microservices architecture, and EKS sizing."
    },
    "training": {
        "key": "training",
        "name": "Training Materials",
        "route": "/training-materials",
        "is_published": True,
        "icon": "fa-book-open-reader",
        "description": "Live sync of ArtisanTek curriculum, AWS labs, Kubernetes, Docker, and Linux guides."
    },
    "cheatsheet": {
        "key": "cheatsheet",
        "name": "Command Cheatsheet",
        "route": "/command-cheatsheet",
        "is_published": True,
        "icon": "fa-terminal",
        "description": "Instant reference for Linux, Bash, Git, Docker, Kubernetes, Terraform, and Ansible."
    },
    "app_logs": {
        "key": "app_logs",
        "name": "App Logs",
        "route": "/app-logs",
        "is_published": True,
        "icon": "fa-server",
        "description": "Live health status of application components, infrastructure mode, and Git audit trail."
    }
}

class PageVisibilityService:
    def __init__(self, storage_file: Optional[str] = None):
        self.storage_path = Path(storage_file or PAGE_VISIBILITY_FILE)
        self._cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._on_change_callbacks: List[Callable[[], None]] = []
        self._ensure_storage()

    def add_on_change_callback(self, cb: Callable[[], None]):
        self._on_change_callbacks.append(cb)

    def _ensure_storage(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._save_to_disk(DEFAULT_PAGES)

    def _save_to_disk(self, data: Dict[str, Dict[str, Any]]):
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self._cache = data
        except Exception as e:
            print(f"Error saving page visibility state: {e}")

    def get_visibility_map(self) -> Dict[str, Dict[str, Any]]:
        if self._cache is not None:
            return self._cache

        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Merge with default pages to ensure any new pages are present
                    merged = dict(DEFAULT_PAGES)
                    for k, v in data.items():
                        if k in merged:
                            merged[k].update(v)
                        else:
                            merged[k] = v
                    self._cache = merged
                    return self._cache
            except Exception:
                pass

        self._cache = dict(DEFAULT_PAGES)
        return self._cache

    def is_page_published(self, page_key: str) -> bool:
        v_map = self.get_visibility_map()
        page = v_map.get(page_key)
        if page:
            return bool(page.get("is_published", True))
        return True

    def set_page_visibility(self, page_key: str, is_published: bool, updated_by: str = "Admin") -> Dict[str, Any]:
        v_map = dict(self.get_visibility_map())
        if page_key not in v_map:
            return {"status": "error", "message": f"Unknown page key: {page_key}"}

        prev_state = v_map[page_key].get("is_published", True)
        v_map[page_key]["is_published"] = is_published
        self._save_to_disk(v_map)

        # Notify callbacks
        for cb in self._on_change_callbacks:
            try:
                cb()
            except Exception:
                pass

        # Log change in human-readable git database audit log
        action_str = "Published (Active)" if is_published else "Hidden (Unpublished)"
        page_name = v_map[page_key].get("name", page_key)
        git_storage_service.log_event(
            event="Page Visibility Changed",
            target=f"Menu: {page_name}",
            details=f"Status set to {action_str} (previous: {'Published' if prev_state else 'Hidden'})",
            triggered_by=updated_by
        )

        return {
            "status": "success",
            "page_key": page_key,
            "page_name": page_name,
            "is_published": is_published,
            "message": f"Successfully updated '{page_name}' to {action_str}."
        }

    def get_first_published_route(self) -> str:
        v_map = self.get_visibility_map()
        ordered_keys = ["question_bank", "project", "training", "cheatsheet", "app_logs"]
        for k in ordered_keys:
            if v_map.get(k, {}).get("is_published", True):
                return v_map[k].get("route", "/question-bank")
        return "/question-bank"

page_visibility_service = PageVisibilityService()
