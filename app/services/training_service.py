import os
import re
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.config import TRAINING_MATERIALS_DIR, NOTES_DIR

class TrainingService:
    def __init__(self, training_dir: Optional[str] = None, notes_dir: Optional[str] = None):
        self.training_dir = Path(training_dir or TRAINING_MATERIALS_DIR)
        self.notes_dir = Path(notes_dir or NOTES_DIR)

    def get_repo_tree(self, repo_id: str) -> Dict[str, Any]:
        """Builds hierarchical folder/file tree for a repository."""
        if repo_id == "training":
            root_dir = self.training_dir
            repo_name = "ArtisanTek Training Materials"
        elif repo_id == "notes":
            root_dir = self.notes_dir
            repo_name = "DevOps Notes Repo"
        else:
            root_dir = self.training_dir
            repo_name = "Training Materials"

        if not root_dir.exists():
            return {"name": repo_name, "type": "directory", "children": []}

        return {
            "name": repo_name,
            "type": "directory",
            "path": "",
            "children": self._scan_directory(root_dir, root_dir)
        }

    def _scan_directory(self, current_dir: Path, base_dir: Path) -> List[Dict[str, Any]]:
        nodes = []
        try:
            entries = sorted(list(current_dir.iterdir()), key=lambda e: (not e.is_dir(), e.name.lower()))
            for entry in entries:
                # Skip hidden or ignored files
                if entry.name.startswith(".") or entry.name == "devops-notes-portal-web-app":
                    continue

                rel_path = str(entry.relative_to(base_dir)).replace("\\", "/")

                if entry.is_dir():
                    children = self._scan_directory(entry, base_dir)
                    if children or not any(entry.iterdir()):
                        nodes.append({
                            "name": entry.name,
                            "type": "directory",
                            "path": rel_path,
                            "children": children
                        })
                else:
                    if entry.suffix.lower() in [".md", ".txt", ".yaml", ".yml", ".json", ".sh", ".py", ".png", ".jpg", ".jpeg", ".svg"]:
                        nodes.append({
                            "name": entry.name,
                            "type": "file",
                            "path": rel_path,
                            "extension": entry.suffix.lower().lstrip(".")
                        })
        except Exception as e:
            print(f"Error scanning directory {current_dir}: {e}")

        return nodes

    def get_file_content(self, repo_id: str, file_path: str) -> Dict[str, Any]:
        """Reads and formats file content."""
        if repo_id == "training":
            base_dir = self.training_dir
        elif repo_id == "notes":
            base_dir = self.notes_dir
        else:
            base_dir = self.training_dir

        # Sanitize path to prevent directory traversal
        clean_rel = Path(file_path).as_posix().lstrip("/").replace("../", "")
        full_path = (base_dir / clean_rel).resolve()

        # Security check: must reside within base_dir
        try:
            full_path.relative_to(base_dir.resolve())
        except ValueError:
            return {"error": "Invalid file path", "content": ""}

        if not full_path.exists() or not full_path.is_file():
            return {"error": f"File '{file_path}' not found", "content": ""}

        try:
            # Check if binary (image)
            suffix = full_path.suffix.lower()
            if suffix in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"]:
                return {
                    "is_image": True,
                    "filename": full_path.name,
                    "path": file_path,
                    "raw_url": f"/api/training/raw/{repo_id}/{clean_rel}"
                }

            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            formatted_markdown = self._format_markdown_qa_and_mermaid(content, repo_id, clean_rel)

            return {
                "is_image": False,
                "filename": full_path.name,
                "path": file_path,
                "raw_content": content,
                "formatted_content": formatted_markdown
            }
        except Exception as e:
            return {"error": f"Error reading file: {str(e)}", "content": ""}

    def fetch_live_github_content(self, repo_url: str, branch: str = "main", file_path: str = "README.md") -> Dict[str, Any]:
        """Fetches live content directly from GitHub repository."""
        # Convert github url to raw githubusercontent url
        # e.g. https://github.com/owner/repo -> https://raw.githubusercontent.com/owner/repo/branch/file_path
        m = re.match(r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$', repo_url.strip())
        if not m:
            return {"error": "Invalid GitHub repository URL"}

        owner, repo = m.group(1), m.group(2)
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"
        try:
            resp = requests.get(raw_url, timeout=10)
            if resp.status_code == 200:
                formatted = self._format_markdown_qa_and_mermaid(resp.text, "custom", file_path)
                return {
                    "owner": owner,
                    "repo": repo,
                    "file_path": file_path,
                    "raw_content": resp.text,
                    "formatted_content": formatted
                }
            else:
                return {"error": f"GitHub returned status {resp.status_code} for {raw_url}"}
        except Exception as e:
            return {"error": f"Live GitHub fetch error: {str(e)}"}

    def _format_markdown_qa_and_mermaid(self, text: str, repo_id: str, current_path: str) -> str:
        """
        Enhances Markdown:
        1. Ensures all QA answers default to collapsed state.
        2. Formats ```mermaid code blocks into <div class="mermaid">.
        3. Normalizes image links to load through our image proxy or raw endpoint.
        """
        # 1. Flowchart / Mermaid formatting
        def replace_mermaid(match):
            code = match.group(1).strip()
            return f'\n<div class="mermaid">\n{code}\n</div>\n'

        text = re.sub(r'```mermaid\s*([\s\S]*?)```', replace_mermaid, text, flags=re.IGNORECASE)

        # 2. Make question/answer blocks collapsed by default
        # If open <details open>, remove open
        text = re.sub(r'<details\s+open\b[^>]*>', '<details class="notes-qa-accordion">', text, flags=re.IGNORECASE)
        text = re.sub(r'<details>', '<details class="notes-qa-accordion">', text, flags=re.IGNORECASE)

        # 3. Detect relative images and point to app proxy
        def replace_img(match):
            alt = match.group(1)
            src = match.group(2)
            if not src.startswith("http://") and not src.startswith("https://") and not src.startswith("/"):
                # Resolve relative path
                parent_dir = str(Path(current_path).parent).replace("\\", "/")
                if parent_dir == ".":
                    full_img_rel = src.lstrip("./")
                else:
                    full_img_rel = f"{parent_dir}/{src.lstrip('./')}"
                src = f"/api/training/raw/{repo_id}/{full_img_rel}"
            return f'![{alt}]({src})'

        text = re.sub(r'!\[(.*?)\]\((.*?)\)', replace_img, text)

        return text

training_service = TrainingService()
