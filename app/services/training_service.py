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

    def get_combined_trees(self) -> List[Dict[str, Any]]:
        """Returns folder trees for both default repositories (ArtisanTek Training and DevOps Notes)."""
        trees = []

        # 1. ArtisanTek Training Materials
        if self.training_dir.exists():
            trees.append({
                "repo_id": "training",
                "name": "ArtisanTek Training Materials",
                "icon": "fa-graduation-cap",
                "type": "directory",
                "path": "",
                "children": self._scan_directory(self.training_dir, self.training_dir, "training")
            })

        # 2. DevOps Notes Repo
        if self.notes_dir.exists():
            trees.append({
                "repo_id": "notes",
                "name": "DevOps Notes Repo",
                "icon": "fa-book-bookmark",
                "type": "directory",
                "path": "",
                "children": self._scan_directory(self.notes_dir, self.notes_dir, "notes")
            })

        return trees

    def get_repo_tree(self, repo_id: str) -> Dict[str, Any]:
        """Builds hierarchical folder/file tree for a repository."""
        if repo_id == "training":
            root_dir = self.training_dir
            repo_name = "ArtisanTek Training Materials"
            icon = "fa-graduation-cap"
        elif repo_id == "notes":
            root_dir = self.notes_dir
            repo_name = "DevOps Notes Repo"
            icon = "fa-book-bookmark"
        else:
            root_dir = self.training_dir
            repo_name = "Training Materials"
            icon = "fa-folder"

        if not root_dir.exists():
            return {"repo_id": repo_id, "name": repo_name, "icon": icon, "type": "directory", "children": []}

        return {
            "repo_id": repo_id,
            "name": repo_name,
            "icon": icon,
            "type": "directory",
            "path": "",
            "children": self._scan_directory(root_dir, root_dir, repo_id)
        }

    def _scan_directory(self, current_dir: Path, base_dir: Path, repo_id: str = "training") -> List[Dict[str, Any]]:
        nodes = []
        try:
            entries = sorted(list(current_dir.iterdir()), key=lambda e: (not e.is_dir(), e.name.lower()))
            for entry in entries:
                # Skip hidden or ignored files
                if entry.name.startswith(".") or entry.name == "devops-notes-portal-web-app":
                    continue

                rel_path = str(entry.relative_to(base_dir)).replace("\\", "/")

                if entry.is_dir():
                    children = self._scan_directory(entry, base_dir, repo_id)
                    if children or not any(entry.iterdir()):
                        nodes.append({
                            "repo_id": repo_id,
                            "name": entry.name,
                            "type": "directory",
                            "path": rel_path,
                            "children": children
                        })
                else:
                    if entry.suffix.lower() in [".md", ".txt", ".yaml", ".yml", ".json", ".sh", ".py", ".png", ".jpg", ".jpeg", ".svg"]:
                        nodes.append({
                            "repo_id": repo_id,
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
                    "repo_id": repo_id,
                    "filename": full_path.name,
                    "path": file_path,
                    "raw_url": f"/api/training/raw/{repo_id}/{clean_rel}"
                }

            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            formatted_markdown = self._format_markdown_qa_and_mermaid(content, repo_id, clean_rel)

            return {
                "is_image": False,
                "repo_id": repo_id,
                "filename": full_path.name,
                "path": file_path,
                "raw_content": content,
                "formatted_content": formatted_markdown
            }
        except Exception as e:
            return {"error": f"Error reading file: {str(e)}", "content": ""}

    def search_files(self, query: str, repo_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Performs full-text search across all markdown/text files in training materials and notes."""
        query = query.strip()
        if not query or len(query) < 2:
            return []

        q_lower = query.lower()
        results = []

        repos_to_search = []
        if not repo_id or repo_id == "all":
            repos_to_search = [
                ("training", self.training_dir, "ArtisanTek Training Materials"),
                ("notes", self.notes_dir, "DevOps Notes Repo")
            ]
        elif repo_id == "training":
            repos_to_search = [("training", self.training_dir, "ArtisanTek Training Materials")]
        elif repo_id == "notes":
            repos_to_search = [("notes", self.notes_dir, "DevOps Notes Repo")]

        for r_id, base_dir, r_name in repos_to_search:
            if not base_dir.exists():
                continue
            for root, dirs, files in os.walk(base_dir):
                # Skip hidden or vendor dirs
                dirs[:] = [d for d in dirs if not d.startswith(".") and d != "devops-notes-portal-web-app"]
                for file in sorted(files):
                    if not file.lower().endswith((".md", ".txt", ".sh", ".yaml", ".yml", ".json")):
                        continue
                    file_full = Path(root) / file
                    try:
                        with open(file_full, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()

                        if q_lower not in content.lower():
                            continue

                        rel_path = str(file_full.relative_to(base_dir)).replace("\\", "/")
                        lines = content.splitlines()
                        file_matches = 0
                        snippets = []

                        for idx, line in enumerate(lines, start=1):
                            if q_lower in line.lower():
                                file_matches += line.lower().count(q_lower)
                                if len(snippets) < 4:
                                    snippets.append({
                                        "line": idx,
                                        "text": line.strip()[:180]
                                    })

                        if file_matches > 0:
                            results.append({
                                "repo_id": r_id,
                                "repo_name": r_name,
                                "file_path": rel_path,
                                "filename": file,
                                "match_count": file_matches,
                                "snippets": snippets
                            })
                    except Exception:
                        continue

        results.sort(key=lambda x: x["match_count"], reverse=True)
        return results[:60]

    def fetch_github_repo_tree(self, repo_url: str, branch: Optional[str] = None) -> Dict[str, Any]:
        """Fetches full recursive folder/file tree from GitHub Git Trees API."""
        m = re.match(r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$', repo_url.strip())
        if not m:
            return {"error": "Invalid GitHub repository URL", "tree": []}

        owner, repo = m.group(1), m.group(2)
        headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "DevOps-Hub-Portal"}

        try:
            target_branch = branch
            if not target_branch:
                repo_resp = requests.get(f"https://api.github.com/repos/{owner}/{repo}", headers=headers, timeout=10)
                if repo_resp.status_code == 200:
                    target_branch = repo_resp.json().get("default_branch", "main")
                else:
                    target_branch = "main"

            tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{target_branch}?recursive=1"
            tree_resp = requests.get(tree_url, headers=headers, timeout=15)
            if tree_resp.status_code != 200 and target_branch == "main":
                target_branch = "master"
                tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{target_branch}?recursive=1"
                tree_resp = requests.get(tree_url, headers=headers, timeout=15)

            if tree_resp.status_code != 200:
                return {
                    "error": f"Failed to fetch GitHub tree (HTTP {tree_resp.status_code})",
                    "tree": []
                }

            tree_data = tree_resp.json()
            raw_tree = tree_data.get("tree", [])

            repo_id = f"custom_{owner}_{repo}"
            root_dict: Dict[str, Any] = {}

            for item in raw_tree:
                item_path = item.get("path", "")
                if not item_path or item_path.startswith("."):
                    continue
                parts = item_path.split("/")
                curr = root_dict
                for i, part in enumerate(parts):
                    is_file = (i == len(parts) - 1 and item.get("type") == "blob")
                    if part not in curr:
                        curr[part] = {
                            "__is_file__": is_file,
                            "__path__": item_path if is_file else "/".join(parts[:i+1]),
                            "__children__": {}
                        }
                    curr = curr[part]["__children__"]

            def build_nodes(d: Dict[str, Any]) -> List[Dict[str, Any]]:
                nodes = []
                for name, info in sorted(d.items(), key=lambda x: (x[1]["__is_file__"], x[0].lower())):
                    if info["__is_file__"]:
                        ext = name.split(".")[-1].lower() if "." in name else ""
                        nodes.append({
                            "repo_id": repo_id,
                            "name": name,
                            "type": "file",
                            "path": info["__path__"],
                            "extension": ext
                        })
                    else:
                        children = build_nodes(info["__children__"])
                        nodes.append({
                            "repo_id": repo_id,
                            "name": name,
                            "type": "directory",
                            "path": info["__path__"],
                            "children": children
                        })
                return nodes

            children = build_nodes(root_dict)
            return {
                "repo_id": repo_id,
                "owner": owner,
                "repo": repo,
                "branch": target_branch,
                "name": f"{owner}/{repo}",
                "tree": children
            }
        except Exception as e:
            return {"error": f"Error fetching GitHub tree: {str(e)}", "tree": []}

    def fetch_live_github_content(self, repo_url: str, branch: str = "main", file_path: str = "README.md") -> Dict[str, Any]:
        """Fetches live content directly from GitHub repository."""
        m = re.match(r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$', repo_url.strip())
        if not m:
            return {"error": "Invalid GitHub repository URL"}

        owner, repo = m.group(1), m.group(2)
        clean_fp = file_path.lstrip("./")
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{clean_fp}"
        try:
            resp = requests.get(raw_url, timeout=10)
            if resp.status_code == 200:
                formatted = self._format_markdown_qa_and_mermaid(resp.text, f"custom_{owner}_{repo}", clean_fp)
                return {
                    "owner": owner,
                    "repo": repo,
                    "file_path": clean_fp,
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
        2. Formats and sanitizes ```mermaid code blocks into <div class="mermaid">.
        3. Normalizes image links (relative & raw.githubusercontent.com) to load through local raw endpoint.
        """
        # 1. Flowchart / Mermaid formatting & syntax sanitation
        def replace_mermaid(match):
            code = match.group(1)

            # Rewrite any raw.githubusercontent image URLs within the mermaid block to local API endpoint
            code = re.sub(
                r'https?://raw\.githubusercontent\.com/artisantek/training-materials/(?:master|main)/',
                '/api/training/raw/training/',
                code
            )
            code = re.sub(
                r'https?://raw\.githubusercontent\.com/nagaraj602/Notes/(?:master|main)/',
                '/api/training/raw/notes/',
                code
            )

            # Convert 3 or more hyphens to standard -->
            code = re.sub(r'-{3,}>', '-->', code)

            # Sanitize node labels with special characters like ** to quoted strings for Mermaid v11
            def sanitize_labels(m):
                nid = m.group(1)
                content = m.group(2).strip()
                if content.startswith('"') and content.endswith('"'):
                    return f'{nid}[{content}]'
                clean_content = content.replace('"', "'")
                return f'{nid}["{clean_content}"]'

            code = re.sub(r'([A-Za-z0-9_]+)\[([^\]\n]+)\]', sanitize_labels, code)

            # Strip empty lines
            code_lines = [l for l in code.splitlines() if l.strip()]
            clean_code = "\n".join(code_lines)

            return f'\n<div class="mermaid">\n{clean_code}\n</div>\n'

        text = re.sub(r'```mermaid\s*([\s\S]*?)```', replace_mermaid, text, flags=re.IGNORECASE)

        # 2. Make question/answer blocks collapsed by default
        text = re.sub(r'<details\s+open\b[^>]*>', '<details class="notes-qa-accordion">', text, flags=re.IGNORECASE)
        text = re.sub(r'<details>', '<details class="notes-qa-accordion">', text, flags=re.IGNORECASE)

        # 3. Rewrite raw.githubusercontent.com URLs for known repos to local raw API endpoints
        text = re.sub(r'https?://raw\.githubusercontent\.com/artisantek/training-materials/(?:master|main)/', '/api/training/raw/training/', text)
        text = re.sub(r'https?://raw\.githubusercontent\.com/nagaraj602/Notes/(?:master|main)/', '/api/training/raw/notes/', text)

        # 4. Detect relative images and point to app proxy
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

        # 5. Detect relative HTML <img> tags and point to app proxy
        def replace_html_img(match):
            full_tag = match.group(0)
            src = match.group(1)
            if not src.startswith("http://") and not src.startswith("https://") and not src.startswith("/"):
                parent_dir = str(Path(current_path).parent).replace("\\", "/")
                if parent_dir == ".":
                    full_img_rel = src.lstrip("./")
                else:
                    full_img_rel = f"{parent_dir}/{src.lstrip('./')}"
                new_src = f"/api/training/raw/{repo_id}/{full_img_rel}"
                return full_tag.replace(src, new_src)
            return full_tag

        text = re.sub(r'<img\b[^>]*?\bsrc=["\']([^"\']+)["\']', replace_html_img, text, flags=re.IGNORECASE)

        return text

training_service = TrainingService()
