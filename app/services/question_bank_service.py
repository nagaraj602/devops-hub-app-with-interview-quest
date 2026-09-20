import os
import re
from typing import Dict, Any, List, Optional
from app.config import INTERVIEW_QUESTIONS_DIR
from app.services.question_categorizer import (
    BASE_CATEGORIES_LIST,
    is_nagaraj_interview_file,
    parse_date_to_timestamp,
    detect_category_from_text,
    get_fallback_answer_for_question
)

try:
    import markdown
except ImportError:
    class _MockMarkdown:
        @staticmethod
        def markdown(text, **kwargs):
            return text.replace("\n", "<br>")
    markdown = _MockMarkdown()

def render_md(text: str) -> str:
    if not text:
        return ""
    try:
        return markdown.markdown(text, extensions=['fenced_code', 'tables', 'nl2br'])
    except Exception:
        return markdown.markdown(text)

class QuestionBankService:
    def __init__(self, questions_dir: Optional[str] = None):
        self.dir_path = questions_dir or INTERVIEW_QUESTIONS_DIR
        self._cache: Optional[Dict[str, Any]] = None

    def get_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        if self._cache is not None and not force_refresh:
            return self._cache

        directory = self.dir_path
        if not os.path.exists(directory):
            return {
                "companies": [],
                "stats": {"total_companies": 0, "total_rounds": 0, "total_questions": 0, "categories": {}, "tech_categories_count": 0},
                "category_pills": [],
                "calendar_events": {}
            }

        companies_map: Dict[str, Dict[str, Any]] = {}
        category_counts: Dict[str, int] = {}
        calendar_events: Dict[str, List[Dict[str, Any]]] = {}
        has_nagaraj_interviews = False

        md_files = []
        for item in sorted(os.listdir(directory)):
            if item.endswith(".md"):
                md_files.append((item, os.path.join(directory, item)))

        for fname, fpath in md_files:
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                    content = fp.read()
            except Exception:
                continue

            is_nagaraj = is_nagaraj_interview_file(fname)
            if is_nagaraj:
                has_nagaraj_interviews = True

            if "0. Basic" in fname or "0_1. General" in fname:
                self._parse_general_guide(fname, content, companies_map, category_counts, is_nagaraj)
            else:
                self._parse_company_interview(fname, content, companies_map, category_counts, is_nagaraj)

        # Finalize rounds list & categories
        for c in companies_map.values():
            c["categories"] = sorted(list(c["categories"]))
            if isinstance(c["rounds"], dict):
                r_list = []
                for r_name, r_data in c["rounds"].items():
                    r_data["categories"] = sorted(list(r_data["categories"]))
                    r_list.append(r_data)
                    
                    r_date = r_data.get("date", "")
                    if r_date and r_date not in ["Recent", "Core Reference"]:
                        clean_d = r_date.split()[0]
                        calendar_events.setdefault(clean_d, []).append({
                            "company": c["company_name"],
                            "round": r_name,
                            "date": r_date,
                            "question_count": len(r_data["questions"])
                        })
                c["rounds"] = r_list

        companies_list = list(companies_map.values())
        # Sort by recently added question banks (newest file_order first), then interview timestamp descending
        companies_list.sort(key=lambda c: (c.get("file_order", 0.0), c.get("timestamp", 0.0), c["company_name"].lower()), reverse=True)

        total_rounds = sum(len(c["rounds"]) for c in companies_list)
        total_questions = sum(c["total_questions"] for c in companies_list)

        # Build dynamic category list: Include "Nagaraj's Interview" ONLY if matching files exist
        active_categories = list(BASE_CATEGORIES_LIST)
        if has_nagaraj_interviews:
            active_categories.insert(0, "Nagaraj's Interview")

        sorted_categories = []
        for cat in active_categories:
            sorted_categories.append({
                "name": cat,
                "count": category_counts.get(cat, 0)
            })

        self._cache = {
            "companies": companies_list,
            "stats": {
                "total_companies": len(companies_list),
                "total_rounds": total_rounds,
                "total_questions": total_questions,
                "categories": category_counts,
                "tech_categories_count": len(category_counts),
                "has_nagaraj_interviews": has_nagaraj_interviews
            },
            "category_pills": sorted_categories,
            "calendar_events": calendar_events
        }
        return self._cache

    def _parse_company_interview(self, fname: str, content: str, companies_map: Dict[str, Any], category_counts: Dict[str, int], is_nagaraj: bool):
        lines = content.splitlines()
        om = re.search(r'^(\d+(?:_\d+)?)\.', fname)
        file_order = float(om.group(1).replace('_', '.')) if om else 0.0
        dm = re.search(r'(\d{1,2}-[A-Za-z]{3}-\d{4})', fname)
        file_date = dm.group(1) if dm else ""

        current_company_name = ""
        current_round_name = "Round 1"
        current_round_date = ""
        current_category = "Nagaraj's Interview" if is_nagaraj else "General"
        current_q_text = ""
        current_answer_lines = []
        in_answer = False
        is_sub_q = False

        def push_question():
            nonlocal current_q_text, current_answer_lines, in_answer, is_sub_q, current_category, current_round_date
            if not current_q_text:
                return

            q_clean = re.sub(r'^\*+\s*(.*?)\s*\*+:', r'\1:', current_q_text.strip())
            q_clean = re.sub(r'^\*+|\*+$', '', q_clean).strip()
            q_clean = re.sub(r'^[●↳\s]+', '', q_clean).strip()
            q_clean = q_clean.replace('**', '').strip()
            if not q_clean:
                q_clean = current_q_text.strip()

            ans_clean = "\n".join(current_answer_lines).strip()
            ans_clean = re.sub(r'^(?:\*{0,2}Answer:\*{0,2}\s*)', '', ans_clean).strip()

            c_name = current_company_name or "General Company Interviews"
            r_name = current_round_name or "Technical Round"

            if not ans_clean or len(ans_clean) < 15:
                ans_clean = get_fallback_answer_for_question(q_clean, c_name, r_name)

            norm_cat = detect_category_from_text(q_clean, ans_clean, current_category)
            category_counts[norm_cat] = category_counts.get(norm_cat, 0) + 1
            if is_nagaraj:
                category_counts["Nagaraj's Interview"] = category_counts.get("Nagaraj's Interview", 0) + 1

            round_date_val = current_round_date or file_date or "Recent"
            round_ts = parse_date_to_timestamp(round_date_val)

            if c_name not in companies_map:
                companies_map[c_name] = {
                    "company_name": c_name,
                    "rounds": {},
                    "total_questions": 0,
                    "categories": set(),
                    "latest_date": round_date_val,
                    "timestamp": round_ts,
                    "file_order": file_order,
                    "source_file": fname,
                    "is_nagaraj_interview": is_nagaraj
                }
            else:
                companies_map[c_name]["file_order"] = max(companies_map[c_name].get("file_order", 0.0), file_order)
                if is_nagaraj:
                    companies_map[c_name]["is_nagaraj_interview"] = True
                if round_ts > companies_map[c_name].get("timestamp", 0.0) or not companies_map[c_name].get("latest_date"):
                    companies_map[c_name]["timestamp"] = round_ts
                    companies_map[c_name]["latest_date"] = round_date_val

            if r_name not in companies_map[c_name]["rounds"]:
                companies_map[c_name]["rounds"][r_name] = {
                    "round_name": r_name,
                    "date": round_date_val,
                    "timestamp": round_ts,
                    "questions": [],
                    "categories": set()
                }
            else:
                if round_date_val and (not companies_map[c_name]["rounds"][r_name].get("date") or round_ts > companies_map[c_name]["rounds"][r_name].get("timestamp", 0.0)):
                    companies_map[c_name]["rounds"][r_name]["date"] = round_date_val
                    companies_map[c_name]["rounds"][r_name]["timestamp"] = round_ts

            q_id = f"q_{len(category_counts)}_{sum(c.get('total_questions', 0) for c in companies_map.values())}"
            q_entry = {
                "id": q_id,
                "question": q_clean,
                "answer": ans_clean,
                "answer_html": render_md(ans_clean),
                "has_answer": bool(ans_clean),
                "is_sub_q": is_sub_q,
                "category": norm_cat,
                "source_file": fname,
                "is_nagaraj": is_nagaraj
            }

            companies_map[c_name]["rounds"][r_name]["questions"].append(q_entry)
            companies_map[c_name]["rounds"][r_name]["categories"].add(norm_cat)
            companies_map[c_name]["categories"].add(norm_cat)
            if is_nagaraj:
                companies_map[c_name]["categories"].add("Nagaraj's Interview")
                companies_map[c_name]["rounds"][r_name]["categories"].add("Nagaraj's Interview")
            companies_map[c_name]["total_questions"] += 1

            current_q_text = ""
            current_answer_lines = []
            in_answer = False
            is_sub_q = False

        for line in lines:
            line_str = line.strip()
            if not line_str:
                if in_answer:
                    current_answer_lines.append(line)
                continue

            m_date = re.search(r'\*?Date:\s*([^*]+?)\*?$', line_str, re.IGNORECASE)
            if m_date:
                current_round_date = m_date.group(1).strip()
                continue

            m_comp_details = re.search(r'<summary>\s*(?:<h2>)?\s*(?:!\[.*?\]\(.*?\))?\s*(?:🏢)?\s*([A-Za-z0-9\s\.\-_/&]+?)(?:</h2>)?\s*</summary>', line_str, re.IGNORECASE)
            if m_comp_details and not re.search(r'<summary>\s*<strong>', line_str):
                push_question()
                raw_c = m_comp_details.group(1).strip()
                if " - " in raw_c or r"\-" in raw_c:
                    parts = re.split(r'\s*(?:\\-|-|–)\s*', raw_c)
                    current_company_name = parts[0].strip()
                    if len(parts) > 1:
                        current_round_name = parts[1].strip()
                else:
                    current_company_name = raw_c
                current_round_date = ""
                current_category = "Nagaraj's Interview" if is_nagaraj else "General"
                continue

            m_round_details = re.search(r'<summary>\s*(?:<h3>)?\s*([A-Za-z0-9\s\.\-_/&]+?)(?:</h3>)?\s*</summary>', line_str, re.IGNORECASE)
            if m_round_details and not re.search(r'<summary>\s*<strong>', line_str) and not m_comp_details:
                push_question()
                current_round_name = m_round_details.group(1).strip()
                current_round_date = ""
                current_category = "Nagaraj's Interview" if is_nagaraj else "General"
                continue

            if ("🏢" in line_str and "**" in line_str) or re.match(r'^##\s+[A-Za-z0-9]', line_str):
                push_question()
                clean = line_str.replace("![🏢]()", "").replace("🏢", "").replace("*", "").replace("#", "").strip()
                clean = clean.replace(r"\-", "-").replace("–", "-")
                parts = [p.strip() for p in clean.split("-") if p.strip()]
                if parts:
                    current_company_name = parts[0]
                    current_round_name = " - ".join(parts[1:]) if len(parts) > 1 else "Level 1"
                current_round_date = ""
                current_category = "Nagaraj's Interview" if is_nagaraj else "General"
                continue

            m_cat = re.search(r'【\s*(.+?)\s*】', line_str)
            if m_cat:
                push_question()
                current_category = m_cat.group(1).strip()
                continue

            m_q_summary = re.search(r'<summary>\s*<strong>\s*(.+?)\s*</strong>\s*</summary>', line_str, re.IGNORECASE)
            if m_q_summary:
                push_question()
                raw_q = m_q_summary.group(1).strip()
                if raw_q.startswith("↳"):
                    is_sub_q = True
                    raw_q = re.sub(r'^↳\s*(?:Follow-up:\s*)?', '', raw_q).strip()
                elif raw_q.startswith("●"):
                    is_sub_q = False
                    raw_q = re.sub(r'^●\s*', '', raw_q).strip()
                current_q_text = raw_q
                in_answer = True
                continue

            if line_str.startswith("</details>"):
                if in_answer:
                    push_question()
                continue

            if line_str.startswith("●") or line_str.startswith("↳"):
                push_question()
                is_sub = line_str.startswith("↳")
                q_text = line_str[1:].strip()
                q_text = re.sub(r'^\*+|\*+$', '', q_text).strip()
                current_q_text = q_text
                is_sub_q = is_sub
                in_answer = True
                continue

            if in_answer:
                current_answer_lines.append(line)

        push_question()

    def _parse_general_guide(self, fname: str, content: str, companies_map: Dict[str, Any], category_counts: Dict[str, int], is_nagaraj: bool):
        lines = content.splitlines()
        comp_name = "DevOps Core Fundamentals" if "0. Basic" in fname else "Production Scenarios & Strategic Recovery"
        current_round = "General Architecture & Behavioral"
        current_cat = "General"
        current_q_text = ""
        current_answer_lines = []
        in_answer = False

        def push_q():
            nonlocal current_q_text, current_answer_lines, in_answer, current_cat
            if not current_q_text:
                return
            ans_clean = "\n".join(current_answer_lines).strip()
            ans_clean = re.sub(r'^(?:\*{0,2}Answer:\*{0,2}\s*)', '', ans_clean).strip()
            q_clean = re.sub(r'^\*+|\*+$', '', current_q_text.strip()).strip()
            if not ans_clean or len(ans_clean) < 15:
                ans_clean = get_fallback_answer_for_question(q_clean, comp_name, current_round)

            norm_cat = detect_category_from_text(q_clean, ans_clean, current_cat)
            category_counts[norm_cat] = category_counts.get(norm_cat, 0) + 1

            q_id = f"gen_{len(category_counts)}_{sum(c.get('total_questions', 0) for c in companies_map.values())}"
            q_entry = {
                "id": q_id,
                "question": q_clean,
                "answer": ans_clean,
                "answer_html": render_md(ans_clean),
                "has_answer": bool(ans_clean),
                "is_sub_q": False,
                "category": norm_cat,
                "source_file": fname,
                "is_nagaraj": is_nagaraj
            }

            file_order = 0.1 if "0_1" in fname else 0.0
            if comp_name not in companies_map:
                companies_map[comp_name] = {
                    "company_name": comp_name,
                    "rounds": {},
                    "total_questions": 0,
                    "categories": set(),
                    "latest_date": "Core Reference",
                    "timestamp": 0.0,
                    "file_order": file_order,
                    "source_file": fname,
                    "is_nagaraj_interview": is_nagaraj
                }
            if current_round not in companies_map[comp_name]["rounds"]:
                companies_map[comp_name]["rounds"][current_round] = {
                    "round_name": current_round,
                    "date": "Core Reference",
                    "timestamp": 0.0,
                    "questions": [],
                    "categories": set()
                }
            companies_map[comp_name]["rounds"][current_round]["questions"].append(q_entry)
            companies_map[comp_name]["rounds"][current_round]["categories"].add(norm_cat)
            companies_map[comp_name]["categories"].add(norm_cat)
            companies_map[comp_name]["total_questions"] += 1

            current_q_text = ""
            current_answer_lines = []
            in_answer = False

        for line in lines:
            line_str = line.strip()
            if not line_str:
                if in_answer:
                    current_answer_lines.append(line)
                continue

            if line_str.startswith("## "):
                push_q()
                current_round = line_str[3:].strip()
                continue

            m_sum = re.search(r'<summary>\s*<strong>\s*(.+?)\s*</strong>\s*</summary>', line_str, re.IGNORECASE)
            if m_sum:
                push_q()
                raw_q = m_sum.group(1).strip()
                raw_q = re.sub(r'^\d+[\.\)]\s*', '', raw_q)
                current_q_text = raw_q
                in_answer = True
                continue

            if line_str.startswith("</details>"):
                if in_answer:
                    push_q()
                continue

            if in_answer:
                current_answer_lines.append(line)

        push_q()

question_bank_service = QuestionBankService()
