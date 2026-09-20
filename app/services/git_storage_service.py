import os
import json
import datetime
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from app.config import AUDIT_LOG_FILE, SYSTEM_STATUS_FILE, BASE_DIR

class GitStorageService:
    """
    Manages human-readable storage and continuous activity logging directly in the Git repository.
    Acts as the database-free persistence layer.
    """
    def __init__(self):
        self.audit_log_path = Path(AUDIT_LOG_FILE)
        self.status_file_path = Path(SYSTEM_STATUS_FILE)
        self._ensure_files()

    def _ensure_files(self):
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.audit_log_path.exists():
            with open(self.audit_log_path, "w", encoding="utf-8") as f:
                f.write("# DevOps Hub Activity & Audit Log\n\n")
                f.write("| Timestamp (IST) | Event | Target / Component | Details / Commit / Status | Triggered By |\n")
                f.write("| :--- | :--- | :--- | :--- | :--- |\n")
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"| {now} | Initialization | Core System | Initialized Git-based Storage System | System Setup |\n")

        if not self.status_file_path.exists():
            self.save_status({
                "application": "DevOps Knowledge Portal & Interview Hub",
                "port": 8926,
                "base_os": "Ubuntu 24.04 LTS",
                "status": "Healthy",
                "last_synced": datetime.datetime.now().isoformat()
            })

    def log_event(self, event: str, target: str, details: str, triggered_by: str = "User"):
        """Appends a new human-readable log entry to logs/audit_log.md."""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sanitized_details = details.replace("|", "\\|").replace("\n", " ")
        log_line = f"| {now} | {event} | {target} | {sanitized_details} | {triggered_by} |\n"
        
        try:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception as e:
            print(f"Error writing to audit log: {e}")

        # Update last_synced in status JSON
        try:
            status = self.get_status()
            status["last_synced"] = now
            status["last_event"] = f"{event} - {target}"
            self.save_status(status)
        except Exception:
            pass

    def get_audit_logs(self, limit: int = 50) -> List[Dict[str, str]]:
        """Reads and parses audit log entries from logs/audit_log.md in reverse chronological order."""
        if not self.audit_log_path.exists():
            return []
        
        entries = []
        try:
            with open(self.audit_log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            for line in lines:
                line = line.strip()
                if line.startswith("|") and not line.startswith("| Timestamp") and not line.startswith("| :---"):
                    parts = [p.strip() for p in line.strip("|").split("|")]
                    if len(parts) >= 5:
                        entries.append({
                            "timestamp": parts[0],
                            "event": parts[1],
                            "target": parts[2],
                            "details": parts[3],
                            "triggered_by": parts[4]
                        })
            entries.reverse()
            return entries[:limit]
        except Exception as e:
            print(f"Error reading audit log: {e}")
            return []

    def get_status(self) -> Dict[str, Any]:
        """Reads system status JSON."""
        if not self.status_file_path.exists():
            return {}
        try:
            with open(self.status_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_status(self, data: Dict[str, Any]):
        """Saves system status JSON."""
        try:
            with open(self.status_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving system status: {e}")

    def commit_and_push_logs(self, commit_msg: str = "chore: update continuous activity audit logs") -> Dict[str, Any]:
        """Optionally commits and pushes changes to git origin main."""
        try:
            subprocess.run(["git", "add", "logs/"], cwd=str(BASE_DIR), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            diff_check = subprocess.run(["git", "diff", "--staged", "--quiet"], cwd=str(BASE_DIR))
            if diff_check.returncode == 0:
                return {"status": "success", "message": "No new log changes to commit."}

            subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(BASE_DIR), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Try push with timeout
            push_res = subprocess.run(["git", "push", "origin", "main"], cwd=str(BASE_DIR), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
            if push_res.returncode == 0:
                return {"status": "success", "message": "Successfully committed and pushed audit logs to GitHub repo."}
            else:
                return {"status": "warning", "message": f"Committed locally. Push notice: {push_res.stderr.strip()}"}
        except Exception as e:
            return {"status": "info", "message": f"Saved logs locally in repository. ({str(e)})"}

git_storage_service = GitStorageService()
