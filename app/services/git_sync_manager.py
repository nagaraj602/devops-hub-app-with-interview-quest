import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from app.config import (
    DEFAULT_REPOS,
    CONTENT_DIR,
    INTERVIEW_QUESTIONS_DIR,
    CHEATSHEET_DIR,
    NOTES_DIR,
    TRAINING_MATERIALS_DIR,
    BASE_DIR
)
from app.services.question_bank_service import question_bank_service
from app.services.cheatsheet_service import cheatsheet_service

class GitSyncManager:
    """
    Manages live synchronization from remote Git repositories into local container storage.
    Pulls updates from https://github.com/nagaraj602/Notes.git and training materials,
    persisting files in the container filesystem so subsequent requests have zero external network latency.
    """
    def __init__(self):
        self.repos_dir = CONTENT_DIR / "repos"
        self.notes_repo_dir = self.repos_dir / "notes"
        self.training_repo_dir = self.repos_dir / "training"
        self.repos_dir.mkdir(parents=True, exist_ok=True)

    def _get_git_executable(self) -> str:
        return shutil.which("git") or "git"

    def _run_git(self, args: list, cwd: Optional[Path] = None, timeout: int = 90) -> Tuple[int, str, str]:
        git_bin = self._get_git_executable()
        try:
            res = subprocess.run(
                [git_bin] + args,
                cwd=str(cwd) if cwd else str(BASE_DIR),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except FileNotFoundError:
            return -1, "", "Git binary not found in system PATH."
        except subprocess.TimeoutExpired:
            return -2, "", f"Git command timed out after {timeout} seconds."
        except Exception as e:
            return -3, "", str(e)

    def _clone_or_update(self, repo_url: str, branch: str, target_dir: Path) -> Tuple[bool, str, str]:
        """
        Idempotently pulls latest commit for target repo.
        If repository is not yet cloned, performs a shallow clone (--depth 1).
        If already cloned, performs git fetch and hard reset to ensure clean, fast sync.
        """
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        git_dir = target_dir / ".git"

        if git_dir.is_dir():
            # 1. Fetch latest changes
            code, out, err = self._run_git(["fetch", "--depth", "1", "origin", branch], cwd=target_dir)
            if code != 0:
                # Fallback: try fetching origin HEAD
                code, out, err = self._run_git(["fetch", "--depth", "1", "origin"], cwd=target_dir)
            
            # 2. Hard reset to origin branch
            code_reset, _, _ = self._run_git(["reset", "--hard", f"origin/{branch}"], cwd=target_dir)
            if code_reset != 0:
                self._run_git(["reset", "--hard", "FETCH_HEAD"], cwd=target_dir)

            self._run_git(["clean", "-fd"], cwd=target_dir)
        else:
            # Clean incomplete directory if exists
            if target_dir.exists():
                try:
                    shutil.rmtree(target_dir, ignore_errors=True)
                except Exception:
                    pass

            # Shallow clone
            code, out, err = self._run_git(["clone", "--depth", "1", "--branch", branch, repo_url, str(target_dir)])
            if code != 0:
                # Try clone without explicit branch (let git pick default branch e.g. master/main)
                code, out, err = self._run_git(["clone", "--depth", "1", repo_url, str(target_dir)])
                if code != 0:
                    return False, "", f"Git clone failed: {err or out}"

        # Retrieve short commit hash
        _, commit_hash, _ = self._run_git(["rev-parse", "--short", "HEAD"], cwd=target_dir)
        return True, commit_hash or "main", "Synchronized successfully"

    def sync_notes_repo(self) -> Dict[str, Any]:
        """
        Synchronizes https://github.com/nagaraj602/Notes.git into the container:
        1. Clones/pulls latest Notes repository.
        2. Copies Old Interview Questions into content/interview_questions.
        3. Copies commands_cheatsheet into content/cheatsheets.
        4. Copies notes into content/notes.
        5. Invalidates in-memory caches and re-indexes questions.
        """
        repo_info = DEFAULT_REPOS["notes"]
        repo_url = repo_info["url"]
        branch = repo_info.get("branch", "main")

        # Fallback check: if scratch/notes_repo exists (local dev), seed from it if clone target is empty
        if not (self.notes_repo_dir / ".git").is_dir():
            local_scratch = BASE_DIR / "scratch" / "notes_repo"
            if (local_scratch / ".git").is_dir():
                try:
                    shutil.copytree(local_scratch, self.notes_repo_dir, dirs_exist_ok=True)
                except Exception:
                    pass

        success, commit_hash, msg = self._clone_or_update(repo_url, branch, self.notes_repo_dir)
        if not success:
            # If network clone fails, attempt using existing local content
            return {
                "status": "warning",
                "commit": "local",
                "message": f"Could not pull from remote: {msg}. Using existing local files."
            }

        # 1. Sync Old Interview Questions
        source_questions_dir = self.notes_repo_dir / "Old Interview Questions"
        target_questions_dir = Path(INTERVIEW_QUESTIONS_DIR)
        target_questions_dir.mkdir(parents=True, exist_ok=True)

        copied_questions = 0
        if source_questions_dir.is_dir():
            for f in source_questions_dir.glob("*.md"):
                dest = target_questions_dir / f.name
                shutil.copy2(f, dest)
                copied_questions += 1

        # 2. Sync commands_cheatsheet
        source_cheatsheets_dir = self.notes_repo_dir / "commands_cheatsheet"
        target_cheatsheets_dir = Path(CHEATSHEET_DIR)
        target_cheatsheets_dir.mkdir(parents=True, exist_ok=True)

        if source_cheatsheets_dir.is_dir():
            for f in source_cheatsheets_dir.glob("*.md"):
                shutil.copy2(f, target_cheatsheets_dir / f.name)

        # 3. Sync general notes
        target_notes_dir = Path(NOTES_DIR)
        target_notes_dir.mkdir(parents=True, exist_ok=True)
        for pattern in ["*notes*.md", "*Notes*.md"]:
            for f in self.notes_repo_dir.glob(pattern):
                shutil.copy2(f, target_notes_dir / f.name)

        for folder in ["Kubernetes", "Terraform", "Jenkins-Assignment"]:
            src_f = self.notes_repo_dir / folder
            if src_f.is_dir():
                shutil.copytree(src_f, target_notes_dir / folder, dirs_exist_ok=True)

        # 4. Force refresh in-memory and pickle caches
        data = question_bank_service.get_data(force_refresh=True)
        cheatsheet_service.get_data(force_refresh=True)

        total_q = data["stats"]["total_questions"]
        total_c = data["stats"]["total_companies"]
        total_r = data["stats"]["total_rounds"]

        return {
            "status": "success",
            "commit": commit_hash,
            "total_questions": total_q,
            "total_companies": total_c,
            "total_rounds": total_r,
            "copied_files": copied_questions,
            "message": f"Successfully pulled latest interview questions from Notes repo ({commit_hash}). Synced {total_q} questions across {total_c} companies and {total_r} rounds."
        }

    def sync_training_repo(self) -> Dict[str, Any]:
        """
        Synchronizes https://github.com/artisantek/training-materials.git into content/training_materials.
        """
        repo_info = DEFAULT_REPOS["training"]
        repo_url = repo_info["url"]
        branch = repo_info.get("branch", "master")

        success, commit_hash, msg = self._clone_or_update(repo_url, branch, self.training_repo_dir)
        if not success:
            return {
                "status": "warning",
                "commit": "local",
                "message": f"Training materials sync notice: {msg}"
            }

        # Mirror into TRAINING_MATERIALS_DIR
        target_dir = Path(TRAINING_MATERIALS_DIR)
        target_dir.mkdir(parents=True, exist_ok=True)
        
        for item in self.training_repo_dir.iterdir():
            if item.name == ".git":
                continue
            dest = target_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

        return {
            "status": "success",
            "commit": commit_hash,
            "message": f"Successfully synchronized ArtisanTek training materials (commit {commit_hash})."
        }

    def get_repo_commit(self, repo_id: str) -> str:
        """Returns the current local Git commit hash for the specified repository."""
        if repo_id == "notes":
            if (self.notes_repo_dir / ".git").is_dir():
                _, commit, _ = self._run_git(["rev-parse", "--short", "HEAD"], cwd=self.notes_repo_dir)
                if commit:
                    return commit
            local_scratch = BASE_DIR / "scratch" / "notes_repo"
            if (local_scratch / ".git").is_dir():
                _, commit, _ = self._run_git(["rev-parse", "--short", "HEAD"], cwd=local_scratch)
                if commit:
                    return commit
            return "origin/main"

        elif repo_id == "training":
            if (self.training_repo_dir / ".git").is_dir():
                _, commit, _ = self._run_git(["rev-parse", "--short", "HEAD"], cwd=self.training_repo_dir)
                if commit:
                    return commit
            return "master"

        elif repo_id == "hub_storage":
            _, commit, _ = self._run_git(["rev-parse", "--short", "HEAD"], cwd=BASE_DIR)
            return commit or "main"

        return "Ready"

git_sync_manager = GitSyncManager()
