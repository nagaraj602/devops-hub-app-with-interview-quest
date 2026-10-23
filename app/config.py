import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
CONTENT_DIR = BASE_DIR / "content"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
os.makedirs(CONTENT_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Port & Server settings
PORT = int(os.getenv("PORT", "8926"))
HOST = os.getenv("HOST", "0.0.0.0")
ADMIN_PORT = int(os.getenv("ADMIN_PORT", "9256"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "GET/app-logs200OK(~47ms)")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "f90dcbc73376e144ca034c82aa4980b11c6c13985a4f4ed09904686502760d5f")
ADMIN_PASSWORD_SALT = os.getenv("ADMIN_PASSWORD_SALT", "devops_hub_admin_salt_2026").encode("utf-8")

# Content directories
INTERVIEW_QUESTIONS_DIR = os.getenv("INTERVIEW_QUESTIONS_DIR", str(CONTENT_DIR / "interview_questions"))
QA_SESSIONS_DIR = os.getenv("QA_SESSIONS_DIR", str(CONTENT_DIR / "qa_sessions"))
CHEATSHEET_DIR = os.getenv("CHEATSHEET_DIR", str(CONTENT_DIR / "cheatsheets"))
NOTES_DIR = os.getenv("NOTES_DIR", str(CONTENT_DIR / "notes"))
TRAINING_MATERIALS_DIR = os.getenv("TRAINING_MATERIALS_DIR", str(CONTENT_DIR / "training_materials"))
PROJECT_FILE = os.getenv("PROJECT_FILE", str(BASE_DIR / "Project"))

# Git Storage & Continuous Logs
AUDIT_LOG_FILE = os.getenv("AUDIT_LOG_FILE", str(LOGS_DIR / "audit_log.md"))
SYSTEM_STATUS_FILE = os.getenv("SYSTEM_STATUS_FILE", str(LOGS_DIR / "system_status.json"))
PAGE_VISIBILITY_FILE = os.getenv("PAGE_VISIBILITY_FILE", str(LOGS_DIR / "page_visibility.json"))

# Default Git Repositories
DEFAULT_REPOS = {
    "hub_storage": {
        "name": "DevOps Hub App & Git Database",
        "url": "https://github.com/nagaraj602/devops-hub-app-with-interview-quest.git",
        "branch": "main",
        "description": "Primary Git database storing application source code, human-readable data, and continuous audit logs."
    },
    "notes": {
        "name": "DevOps Notes & Interview Questions",
        "url": "https://github.com/nagaraj602/Notes.git",
        "branch": "main",
        "description": "Repository containing Old Interview Questions, Linux, Docker, AWS, and Kubernetes notes."
    },
    "training": {
        "name": "ArtisanTek Training Materials",
        "url": "https://github.com/artisantek/training-materials.git",
        "branch": "master",
        "description": "Comprehensive DevOps hands-on curriculum, labs, AWS, K8s, Jenkins, and Linux modules."
    }
}
