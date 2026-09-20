import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.config import CHEATSHEET_DIR

CHEATSHEET_CATEGORY_MAPPING = [
    {"id": "all", "name": "All Categories", "file": None, "icon": "fa-layer-group"},
    {"id": "linux", "name": "Linux", "file": "linux.md", "icon": "fa-terminal"},
    {"id": "shell_script", "name": "Shell Script", "file": "shell_script.md", "icon": "fa-scroll"},
    {"id": "github", "name": "Github", "file": "github.md", "icon": "fa-code-branch"},
    {"id": "build_tools", "name": "Build Tools (Maven, Python, C, NodeJS)", "file": "build_tools.md", "icon": "fa-cubes"},
    {"id": "aws", "name": "AWS", "file": "aws.md", "icon": "fa-cloud"},
    {"id": "docker", "name": "Docker", "file": "docker.md", "icon": "fa-docker"},
    {"id": "kubernetes", "name": "Kubernetes", "file": "kubernetes.md", "icon": "fa-dharmachakra"},
    {"id": "helm", "name": "Helm", "file": "helm.md", "icon": "fa-anchor"},
    {"id": "terraform", "name": "Terraform", "file": "terraform.md", "icon": "fa-cube"},
    {"id": "ansible", "name": "Ansible", "file": "ansible.md", "icon": "fa-network-wired"},
    {"id": "monitoring", "name": "Monitoring Tools", "file": "monitoring.md", "icon": "fa-chart-line"},
    {"id": "shell_examples", "name": "Shell Script Examples", "file": "shell_examples.md", "icon": "fa-file-code"},
    {"id": "k8s_manifests", "name": "Kubernetes Manifest Files", "file": "k8s_manifests.md", "icon": "fa-file-alt"},
    {"id": "terraform_examples", "name": "Terraform YAML / HCL Examples", "file": "terraform_examples.md", "icon": "fa-file-contract"},
    {"id": "ansible_examples", "name": "Ansible Example Files", "file": "ansible_examples.md", "icon": "fa-file-invoice"},
    {"id": "dockerfile_examples", "name": "Dockerfile Example Files", "file": "dockerfile_examples.md", "icon": "fa-file-shield"}
]

class CheatsheetService:
    def __init__(self, cheatsheet_dir: Optional[str] = None):
        self.cheatsheet_dir = Path(cheatsheet_dir or CHEATSHEET_DIR)
        self._cached_data: Optional[Dict[str, Any]] = None

    def get_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        if self._cached_data is not None and not force_refresh:
            return self._cached_data

        categories_data = []
        all_items = []
        category_counts = {}

        for meta in CHEATSHEET_CATEGORY_MAPPING:
            fname = meta.get("file")
            if not fname:
                continue

            file_path = self.cheatsheet_dir / fname
            if not file_path.exists():
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue

            items = self._parse_cheatsheet_content(content, meta["name"], meta["id"])
            category_counts[meta["id"]] = len(items)
            all_items.extend(items)

            categories_data.append({
                "id": meta["id"],
                "name": meta["name"],
                "icon": meta["icon"],
                "count": len(items),
                "items": items
            })

        self._cached_data = {
            "categories": CHEATSHEET_CATEGORY_MAPPING,
            "category_details": categories_data,
            "all_items": all_items,
            "total_commands": len(all_items),
            "counts": category_counts
        }
        return self._cached_data

    def _parse_cheatsheet_content(self, text: str, category_name: str, category_id: str) -> List[Dict[str, Any]]:
        items = []
        lines = text.splitlines()

        current_section = "General Commands"
        in_table = False
        col_map: Dict[str, int] = {}

        # Also support code block example files
        in_code_block = False
        current_code_title = ""
        current_code_lang = ""
        current_code_lines = []
        current_code_desc = ""

        for line in lines:
            trimmed = line.strip()

            # Detect code fence
            if trimmed.startswith("```"):
                if in_code_block:
                    # Closing code block
                    code_text = "\n".join(current_code_lines).strip()
                    if code_text:
                        items.append({
                            "type": "code",
                            "category_id": category_id,
                            "category_name": category_name,
                            "section": current_section,
                            "title": current_code_title or "Code Example",
                            "explanation": current_code_desc or "Practical DevOps infrastructure example.",
                            "command": code_text,
                            "language": current_code_lang or "bash",
                            "flags": "",
                            "tags": [category_name, "Example", current_code_lang or "code"]
                        })
                    in_code_block = False
                    current_code_lines = []
                    current_code_title = ""
                    current_code_desc = ""
                    continue
                else:
                    in_code_block = True
                    current_code_lang = trimmed.replace("```", "").strip()
                    continue

            if in_code_block:
                current_code_lines.append(line)
                continue

            # Check for section header (## 1. System Navigation & Directory Operations)
            section_match = re.match(r"^#{2,3}\s+(?:(?:\d+[\.\)]\s*)?)(.+)$", trimmed)
            if section_match and not trimmed.startswith("### Key") and not trimmed.startswith("### Core"):
                candidate_section = section_match.group(1).strip()
                candidate_section = re.sub(r"[*_`]", "", candidate_section).strip()
                if candidate_section and not candidate_section.lower().startswith("table of"):
                    current_section = candidate_section
                    current_code_title = candidate_section
                    in_table = False
                    col_map = {}
                    continue

            # Look for example description lines before code blocks
            if trimmed.startswith("**Description**:") or trimmed.startswith("**Usage**:"):
                current_code_desc = trimmed.split(":", 1)[1].strip()
                continue

            # Check for table rows
            if trimmed.startswith("|") and trimmed.endswith("|"):
                raw_cells = trimmed.strip("|").split("|")
                cells = [c.strip() for c in raw_cells]

                # Detect Header Row
                if not in_table:
                    lower_cells = [c.lower() for c in cells]
                    if any("command" in c or "instruction" in c or "step" in c for c in lower_cells):
                        in_table = True
                        col_map = {}
                        for idx, c in enumerate(lower_cells):
                            if "command" in c or "instruction" in c or "action" in c:
                                col_map["command"] = idx
                            elif "description" in c or "explanation" in c or "purpose" in c or "meaning" in c:
                                col_map["explanation"] = idx
                            elif "flag" in c or "syntax" in c or "option" in c:
                                col_map["flags"] = idx
                            elif "tag" in c or "category" in c or "example" in c:
                                col_map["tags"] = idx
                        if "explanation" not in col_map and len(cells) > 1:
                            col_map["explanation"] = 1
                        continue

                # Skip separator line
                if re.match(r"^[\s\-:|]+$", trimmed):
                    continue

                # Data Row
                if in_table and len(cells) >= 2:
                    cmd_idx = col_map.get("command", 0)
                    exp_idx = col_map.get("explanation", 1)
                    flags_idx = col_map.get("flags")
                    tags_idx = col_map.get("tags")

                    raw_cmd = cells[cmd_idx] if cmd_idx < len(cells) else ""
                    cmd = raw_cmd.strip("`").strip()
                    explanation = cells[exp_idx] if exp_idx < len(cells) else ""
                    
                    flags = ""
                    if flags_idx is not None and flags_idx < len(cells):
                        flags = cells[flags_idx].strip()

                    tags_str = ""
                    if tags_idx is not None and tags_idx < len(cells):
                        tags_str = cells[tags_idx].strip()
                    elif flags_idx is None and len(cells) > 2:
                        tags_str = cells[2].strip()

                    tags = [t.strip() for t in tags_str.replace("`", "").split(",") if t.strip()]
                    if not tags:
                        tags = [category_name]

                    if cmd:
                        items.append({
                            "type": "command",
                            "category_id": category_id,
                            "category_name": category_name,
                            "section": current_section,
                            "command": cmd,
                            "explanation": explanation,
                            "flags": flags,
                            "tags": tags
                        })

        return items

cheatsheet_service = CheatsheetService()
