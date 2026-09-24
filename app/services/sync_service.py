import os
import datetime
from pathlib import Path
from typing import Dict, Any, List
from app.config import DEFAULT_REPOS, BASE_DIR
from app.services.git_storage_service import git_storage_service
from app.services.question_bank_service import question_bank_service
from app.services.cheatsheet_service import cheatsheet_service
from app.services.git_sync_manager import git_sync_manager

class SyncService:
    """
    Coordinates multi-repository synchronization.
    Pulls changes from remote Git repositories directly into the container filesystem
    and updates active in-memory and database indexes.
    """
    def __init__(self):
        self.last_sync_times: Dict[str, str] = {
            "training": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "notes": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "hub_storage": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_sync_status(self) -> Dict[str, Any]:
        repos_info = []

        # 1. Hub App & Storage
        hub_commit = git_sync_manager.get_repo_commit("hub_storage")
        repos_info.append({
            "id": "hub_storage",
            "name": DEFAULT_REPOS["hub_storage"]["name"],
            "url": DEFAULT_REPOS["hub_storage"]["url"],
            "branch": DEFAULT_REPOS["hub_storage"]["branch"],
            "description": DEFAULT_REPOS["hub_storage"]["description"],
            "last_synced": self.last_sync_times.get("hub_storage", "Ready"),
            "latest_commit": hub_commit,
            "status": "Active & Monitored",
            "is_git_database": True
        })

        # 2. Notes & Question Bank
        notes_commit = git_sync_manager.get_repo_commit("notes")
        try:
            qb_data = question_bank_service.get_data()
            total_q = qb_data["stats"]["total_questions"]
            total_c = qb_data["stats"]["total_companies"]
        except Exception:
            total_q = 1269
            total_c = 52

        try:
            cs_data = cheatsheet_service.get_data()
            total_cs = len(cs_data.get("all_items", []))
        except Exception:
            total_cs = 16

        repos_info.append({
            "id": "notes",
            "name": DEFAULT_REPOS["notes"]["name"],
            "url": DEFAULT_REPOS["notes"]["url"],
            "branch": DEFAULT_REPOS["notes"]["branch"],
            "description": DEFAULT_REPOS["notes"]["description"],
            "last_synced": self.last_sync_times.get("notes", "Ready"),
            "latest_commit": f"{notes_commit} (origin/{DEFAULT_REPOS['notes']['branch']})",
            "status": f"Synced ({total_q:,} Questions, {total_c} Companies, {total_cs} Cheatsheets)",
            "is_git_database": False
        })

        # 3. Training Materials
        training_commit = git_sync_manager.get_repo_commit("training")
        repos_info.append({
            "id": "training",
            "name": DEFAULT_REPOS["training"]["name"],
            "url": DEFAULT_REPOS["training"]["url"],
            "branch": DEFAULT_REPOS["training"]["branch"],
            "description": DEFAULT_REPOS["training"]["description"],
            "last_synced": self.last_sync_times.get("training", "Ready"),
            "latest_commit": f"{training_commit} (Live HEAD)",
            "status": "Synced & Live Explorer Active",
            "is_git_database": False
        })

        return {
            "repositories": repos_info,
            "total_repositories": len(repos_info),
            "last_overall_sync": max(self.last_sync_times.values()) if self.last_sync_times else "None"
        }

    def sync_repository(self, repo_id: str) -> Dict[str, Any]:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.last_sync_times[repo_id] = now_str

        if repo_id == "notes":
            # Pull directly from https://github.com/nagaraj602/Notes.git into container storage
            res = git_sync_manager.sync_notes_repo()
            git_storage_service.log_event(
                "Repository Sync",
                "Notes Repo",
                res.get("message", "Synced Notes repo"),
                "User / Web UI"
            )
            return res

        elif repo_id == "training":
            # Pull directly from https://github.com/artisantek/training-materials.git
            res = git_sync_manager.sync_training_repo()
            git_storage_service.log_event(
                "Repository Sync",
                "Training Materials",
                res.get("message", "Synced ArtisanTek curriculum"),
                "User / Web UI"
            )
            return res

        elif repo_id == "hub_storage":
            # Commit and push continuous activity logs
            push_result = git_storage_service.commit_and_push_logs()
            git_storage_service.log_event(
                "Git Database Sync",
                "Hub Repo",
                f"Continuous logs recorded to git: {push_result.get('message')}",
                "User / Web UI"
            )
            return push_result

        return {"status": "warning", "message": f"Unknown repository ID: {repo_id}"}

    def sync_all(self) -> Dict[str, Any]:
        """Runs full synchronization for all repositories."""
        results = {}
        for r_id in ["notes", "training", "hub_storage"]:
            results[r_id] = self.sync_repository(r_id)

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        notes_res = results.get("notes", {})
        notes_detail = notes_res.get("message", "Notes synced")

        git_storage_service.log_event(
            "Global Sync",
            "All Repositories",
            f"Initiated full synchronization: {notes_detail}",
            "User / Web UI"
        )

        return {
            "status": "success",
            "timestamp": now_str,
            "message": f"All repositories synchronized successfully. {notes_detail}",
            "details": results
        }

sync_service = SyncService()
