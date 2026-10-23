import os
import re
import pickle
from typing import Dict, Any, List, Optional, Callable
from collections import Counter
from app.config import INTERVIEW_QUESTIONS_DIR
from app.services.company_logo_service import get_company_logo_meta
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
        self._on_refresh_callbacks: List[Callable[[], None]] = []

    def add_on_refresh_callback(self, cb: Callable[[], None]):
        self._on_refresh_callbacks.append(cb)

    def _get_cache_path(self) -> str:
        return os.path.join(self.dir_path, ".cache_qb.pkl")

    def _compute_fingerprint(self) -> str:
        directory = self.dir_path
        if not os.path.exists(directory):
            return ""
        items = []
        try:
            for f in sorted(os.listdir(directory)):
                if f.endswith(".md"):
                    fp = os.path.join(directory, f)
                    st = os.stat(fp)
                    items.append(f"{f}:{st.st_mtime}:{st.st_size}")
        except Exception:
            pass
        return ";".join(items)

    def get_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        if self._cache is not None and not force_refresh:
            return self._cache

        fingerprint = self._compute_fingerprint()
        cache_path = self._get_cache_path()

        if not force_refresh and os.path.exists(cache_path):
            try:
                with open(cache_path, "rb") as cpf:
                    payload = pickle.load(cpf)
                    if isinstance(payload, dict) and payload.get("fingerprint") == fingerprint:
                        self._cache = payload.get("data")
                        return self._cache
            except Exception:
                pass

        if force_refresh:
            for cb in self._on_refresh_callbacks:
                try:
                    cb()
                except Exception:
                    pass

        directory = self.dir_path
        if not os.path.exists(directory):
            return {
                "companies": [],
                "stats": {"total_companies": 0, "total_rounds": 0, "total_questions": 0, "categories": {}, "tech_categories_count": 0},
                "category_pills": [],
                "calendar_events": {}
            }

        sessions_list: List[Dict[str, Any]] = []
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
                self._parse_general_guide(fname, content, sessions_list, category_counts, is_nagaraj)
            else:
                self._parse_company_interview(fname, content, sessions_list, category_counts, is_nagaraj)

        companies_list = [s for s in sessions_list if s.get("total_questions", 0) > 0]

        # Finalize rounds list & categories and populate calendar events
        for c in companies_list:
            c["categories"] = sorted(list(c["categories"]))
            for r in c.get("rounds", []):
                r["categories"] = sorted(list(r.get("categories", [])))
                r_date = r.get("date", "")
                if r_date and r_date not in ["Recent", "Core Reference", "N/A"]:
                    clean_d = r_date.split()[0]
                    calendar_events.setdefault(clean_d, []).append({
                        "company": c["company_name"],
                        "round": r.get("round_name", ""),
                        "date": r_date,
                        "question_count": len(r.get("questions", []))
                    })

        # By default, sort listings in order of interview date & time descending (most recent first)
        companies_list.sort(key=lambda c: (c.get("timestamp", 0.0), c.get("file_order", 0.0), c["company_name"].lower()), reverse=True)

        unique_companies = len(set(c["company_name"] for c in companies_list if not c.get("is_guide")))
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
                "total_companies": unique_companies,
                "total_rounds": total_rounds,
                "total_questions": total_questions,
                "categories": category_counts,
                "tech_categories_count": len(category_counts),
                "has_nagaraj_interviews": has_nagaraj_interviews
            },
            "category_pills": sorted_categories,
            "calendar_events": calendar_events
        }

        try:
            with open(cache_path, "wb") as cpf:
                pickle.dump({"fingerprint": fingerprint, "data": self._cache}, cpf, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception:
            pass

        return self._cache

    def _parse_company_interview(self, fname: str, content: str, sessions_list: List[Dict[str, Any]], category_counts: Dict[str, int], is_nagaraj: bool):
        lines = content.splitlines()
        om = re.search(r'^(\d+(?:_\d+)?)\.', fname)
        file_order = float(om.group(1).replace('_', '.')) if om else 0.0
        dm = re.search(r'(\d{1,2}-[A-Za-z]{3}-\d{4})', fname)
        file_date = dm.group(1) if dm else ""

        current_company = "General"
        current_round_name = "Level 1"
        current_round_date = ""
        current_category = "Nagaraj's Interview" if is_nagaraj else "General"
        current_q_text = ""
        current_answer_lines: List[str] = []
        in_answer = False
        is_sub_q = False

        current_round_questions: List[Dict[str, Any]] = []
        current_round_categories: set = set()

        def push_question():
            nonlocal current_q_text, current_answer_lines, in_answer, is_sub_q, current_category
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

            c_name = current_company
            r_name = current_round_name or "Technical Round"

            if not ans_clean or len(ans_clean) < 15:
                ans_clean = get_fallback_answer_for_question(q_clean, c_name, r_name)

            norm_cat = detect_category_from_text(q_clean, ans_clean, current_category)
            category_counts[norm_cat] = category_counts.get(norm_cat, 0) + 1
            if is_nagaraj:
                category_counts["Nagaraj's Interview"] = category_counts.get("Nagaraj's Interview", 0) + 1

            q_id = f"q_{len(category_counts)}_{sum(s.get('total_questions', 0) for s in sessions_list) + len(current_round_questions)}"
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

            current_round_questions.append(q_entry)
            current_round_categories.add(norm_cat)
            if is_nagaraj:
                current_round_categories.add("Nagaraj's Interview")

            current_q_text = ""
            current_answer_lines = []
            in_answer = False
            is_sub_q = False

        def push_current_round():
            nonlocal current_round_questions, current_round_categories, current_round_date
            push_question()
            if not current_round_questions:
                return

            round_date_val = current_round_date or file_date or "Recent"
            round_ts = parse_date_to_timestamp(round_date_val)
            logo_meta = get_company_logo_meta(current_company)

            round_obj = {
                "round_name": current_round_name or "Level 1",
                "date": round_date_val,
                "timestamp": round_ts,
                "questions": list(current_round_questions),
                "categories": set(current_round_categories)
            }

            session_obj = {
                "company_name": current_company,
                "rounds": [round_obj],
                "total_questions": len(current_round_questions),
                "categories": set(current_round_categories),
                "latest_date": round_date_val,
                "timestamp": round_ts,
                "file_order": file_order,
                "source_file": fname,
                "is_nagaraj_interview": is_nagaraj,
                "logo_url": logo_meta["logo_url"],
                "initials": logo_meta["initials"],
                "avatar_bg": logo_meta["avatar_bg"],
                "avatar_color": logo_meta["avatar_color"],
                "is_guide": logo_meta["is_guide"],
                "guide_icon": logo_meta["guide_icon"]
            }

            sessions_list.append(session_obj)

            current_round_questions = []
            current_round_categories = set()

        for line in lines:
            line_str = line.strip()
            if not line_str:
                if in_answer:
                    current_answer_lines.append(line)
                continue

            m_date = re.search(r'\*?Date:\s*([^*]+?)\*?$', line_str, re.IGNORECASE)
            if m_date:
                d_val = m_date.group(1).strip()
                if d_val and d_val != "N/A":
                    current_round_date = d_val
                continue

            m_comp_details = re.search(r'<summary>\s*(?:<h2>)?\s*(?:!\[.*?\]\(.*?\))?\s*(?:🏢)?\s*([A-Za-z0-9\s\.\-_/&]+?)(?:</h2>)?\s*</summary>', line_str, re.IGNORECASE)
            if m_comp_details and not re.search(r'<summary>\s*<strong>', line_str):
                push_current_round()
                raw_c = m_comp_details.group(1).strip()
                r_init = "Level 1"
                if " - " in raw_c or r"\-" in raw_c:
                    parts = re.split(r'\s*(?:\\-|-|–)\s*', raw_c)
                    c_clean = parts[0].strip()
                    if len(parts) > 1:
                        r_init = parts[1].strip()
                else:
                    c_clean = raw_c
                current_company = c_clean
                current_round_name = r_init
                current_round_date = ""
                current_category = "Nagaraj's Interview" if is_nagaraj else "General"
                continue

            m_round_details = re.search(r'<summary>\s*(?:<h3>)?\s*([A-Za-z0-9\s\.\-_/&]+?)(?:</h3>)?\s*</summary>', line_str, re.IGNORECASE)
            if m_round_details and not re.search(r'<summary>\s*<strong>', line_str) and not m_comp_details:
                push_current_round()
                current_round_name = m_round_details.group(1).strip()
                current_round_date = ""
                continue

            if ("🏢" in line_str and "**" in line_str) or re.match(r'^##\s+[A-Za-z0-9]', line_str):
                clean = line_str.replace("![🏢]()", "").replace("🏢", "").replace("*", "").replace("#", "").strip()
                clean = clean.replace(r"\-", "-").replace("–", "-")
                parts = [p.strip() for p in clean.split("-") if p.strip()]
                c_clean = parts[0] if parts else "General"
                r_init = " - ".join(parts[1:]) if len(parts) > 1 else "Level 1"
                push_current_round()
                current_company = c_clean
                current_round_name = r_init
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

        push_current_round()

    def _parse_general_guide(self, fname: str, content: str, sessions_list: List[Dict[str, Any]], category_counts: Dict[str, int], is_nagaraj: bool):
        lines = content.splitlines()
        comp_name = "DevOps Core Fundamentals" if "0. Basic" in fname else "Production Scenarios & Strategic Recovery"
        current_round = "General Architecture & Behavioral"
        current_cat = "General"
        current_q_text = ""
        current_answer_lines: List[str] = []
        in_answer = False

        file_order = 0.1 if "0_1" in fname else 0.0
        logo_meta = get_company_logo_meta(comp_name)

        current_session = next((s for s in sessions_list if s["company_name"] == comp_name), None)
        if not current_session:
            current_session = {
                "company_name": comp_name,
                "rounds": [],
                "total_questions": 0,
                "categories": set(),
                "latest_date": "Core Reference",
                "timestamp": 0.0,
                "file_order": file_order,
                "source_file": fname,
                "is_nagaraj_interview": is_nagaraj,
                "logo_url": logo_meta["logo_url"],
                "initials": logo_meta["initials"],
                "avatar_bg": logo_meta["avatar_bg"],
                "avatar_color": logo_meta["avatar_color"],
                "is_guide": logo_meta["is_guide"],
                "guide_icon": logo_meta["guide_icon"]
            }
            sessions_list.append(current_session)

        def push_q():
            nonlocal current_q_text, current_answer_lines, in_answer, current_cat, current_session, current_round
            if not current_q_text:
                return
            ans_clean = "\n".join(current_answer_lines).strip()
            ans_clean = re.sub(r'^(?:\*{0,2}Answer:\*{0,2}\s*)', '', ans_clean).strip()
            q_clean = re.sub(r'^\*+|\*+$', '', current_q_text.strip()).strip()
            if not ans_clean or len(ans_clean) < 15:
                ans_clean = get_fallback_answer_for_question(q_clean, comp_name, current_round)

            norm_cat = detect_category_from_text(q_clean, ans_clean, current_cat)
            category_counts[norm_cat] = category_counts.get(norm_cat, 0) + 1

            q_id = f"gen_{len(category_counts)}_{sum(s.get('total_questions', 0) for s in sessions_list)}"
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

            # Find or create round in session
            matching_round = next((r for r in current_session["rounds"] if r["round_name"] == current_round), None)
            if not matching_round:
                matching_round = {
                    "round_name": current_round,
                    "date": "Core Reference",
                    "timestamp": 0.0,
                    "questions": [],
                    "categories": set()
                }
                current_session["rounds"].append(matching_round)

            matching_round["questions"].append(q_entry)
            matching_round["categories"].add(norm_cat)
            current_session["categories"].add(norm_cat)
            current_session["total_questions"] += 1

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

    def _consolidate_by_company(self, entries: List[Dict[str, Any]], sort_by: str = "date") -> List[Dict[str, Any]]:
        """
        Groups all rounds of the same company under a single company entry.
        If there are multiple rounds with the same round name (e.g. from different dates/candidates),
        they are kept as separate rounds labeled with their dates (e.g. 'L1 22-Oct-2026', 'L1 15-Aug-2026').
        By default, companies are listed in order of their most recent interview date & time.
        """
        grouped: Dict[str, Dict[str, Any]] = {}

        for entry in entries:
            c_name = entry.get("company_name", "").strip()
            c_key = c_name.lower()

            if c_key not in grouped:
                grouped[c_key] = {
                    "company_name": c_name,
                    "rounds": [],
                    "total_questions": 0,
                    "categories": set(),
                    "latest_date": entry.get("latest_date", ""),
                    "timestamp": entry.get("timestamp", 0.0),
                    "file_order": entry.get("file_order", 0.0),
                    "source_file": entry.get("source_file", ""),
                    "is_nagaraj_interview": entry.get("is_nagaraj_interview", False),
                    "logo_url": entry.get("logo_url"),
                    "initials": entry.get("initials"),
                    "avatar_bg": entry.get("avatar_bg"),
                    "avatar_color": entry.get("avatar_color"),
                    "is_guide": entry.get("is_guide", False),
                    "guide_icon": entry.get("guide_icon")
                }

            comp = grouped[c_key]
            if entry.get("is_nagaraj_interview"):
                comp["is_nagaraj_interview"] = True

            if entry.get("timestamp", 0.0) > comp["timestamp"]:
                comp["timestamp"] = entry.get("timestamp", 0.0)
                comp["latest_date"] = entry.get("latest_date", "")

            for cat in entry.get("categories", []):
                comp["categories"].add(cat)

            for r in entry.get("rounds", []):
                comp["rounds"].append(dict(r))

        result = []
        for c_key, comp in grouped.items():
            comp["categories"] = sorted(list(comp["categories"]))
            # Sort rounds newest date first
            comp["rounds"].sort(key=lambda r: (r.get("timestamp", 0.0), r.get("date", "")), reverse=True)

            processed_rounds = [dict(r) for r in comp["rounds"]]
            comp["rounds"] = processed_rounds
            comp["total_questions"] = sum(len(r.get("questions", [])) for r in processed_rounds)
            result.append(comp)

        if sort_by == "name_asc":
            result.sort(key=lambda c: c.get("company_name", "").lower())
        elif sort_by == "name_desc":
            result.sort(key=lambda c: c.get("company_name", "").lower(), reverse=True)
        else:
            # List companies by order of most recent interview date & time
            result.sort(key=lambda c: (c.get("timestamp", 0.0), c.get("file_order", 0.0), c.get("company_name", "").lower()), reverse=True)

        return result

    def filter_companies(
        self,
        category: Optional[str] = "All",
        search: Optional[str] = "",
        sort_by: Optional[str] = "recent",
        favorites: Optional[List[str]] = None,
        target_company: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        data = self.get_data()
        companies = data.get("companies", [])

        # 1. Target company lookup (e.g. from calendar direct link)
        if target_company and target_company.strip():
            t_name = target_company.strip().lower()
            matching_comp = [c for c in companies if c.get("company_name", "").strip().lower() == t_name]
            if not matching_comp:
                matching_comp = [c for c in companies if t_name in c.get("company_name", "").strip().lower()]
            if matching_comp:
                if sort_by == "group_by_company":
                    return self._consolidate_by_company(matching_comp)
                return matching_comp

        fav_set = set(favorites) if favorites else None
        is_filtering_cat = bool(category and category.strip().lower() not in ("all", ""))
        clean_cat = category.strip().lower() if is_filtering_cat else ""
        s = search.strip().lower() if (search and search.strip()) else ""

        # Filter companies / rounds
        if not is_filtering_cat and not s and not fav_set:
            result = list(companies)
        else:
            result = []
            for comp in companies:
                c_name = comp.get("company_name", "").lower()
                is_nagaraj_comp = comp.get("is_nagaraj_interview", False)
                comp_name_matches = bool(s and s in c_name)

                matching_rounds = []
                for r in comp.get("rounds", []):
                    r_name = r.get("round_name", "").lower()
                    round_name_matches = bool(s and s in r_name)

                    matching_qs = []
                    for q in r.get("questions", []):
                        q_id = q.get("id", "")
                        q_cat = q.get("category", "").lower()
                        is_nagaraj_q = q.get("is_nagaraj", False)

                        # Category match
                        if is_filtering_cat:
                            if clean_cat == "nagaraj's interview":
                                if not (is_nagaraj_comp or is_nagaraj_q or q_cat == "nagaraj's interview"):
                                    continue
                            elif q_cat != clean_cat:
                                continue

                        # Favorites match
                        if fav_set is not None:
                            if q_id not in fav_set:
                                continue

                        # Search match
                        if s:
                            q_text = q.get("question", "").lower()
                            q_ans = q.get("answer", "").lower()
                            if not (comp_name_matches or round_name_matches or s in q_cat or s in q_text or s in q_ans):
                                continue

                        matching_qs.append(q)

                    if matching_qs:
                        r_copy = dict(r)
                        r_copy["questions"] = matching_qs
                        matching_rounds.append(r_copy)

                if matching_rounds:
                    c_copy = dict(comp)
                    c_copy["rounds"] = matching_rounds
                    c_copy["total_questions"] = sum(len(r["questions"]) for r in matching_rounds)
                    result.append(c_copy)

        # 2. Sorting & Grouping
        if sort_by == "group_by_company":
            result = self._consolidate_by_company(result)
        elif sort_by == "name_asc":
            result.sort(key=lambda c: c.get("company_name", "").lower())
        elif sort_by == "name_desc":
            result.sort(key=lambda c: c.get("company_name", "").lower(), reverse=True)
        elif sort_by == "most_questions":
            result.sort(key=lambda c: c.get("total_questions", 0), reverse=True)
        elif sort_by == "date":
            result.sort(key=lambda c: c.get("timestamp", 0.0), reverse=True)
        else:  # "recent"
            result.sort(key=lambda c: (c.get("timestamp", 0.0), c.get("file_order", 0.0), c.get("company_name", "").lower()), reverse=True)

        return result

question_bank_service = QuestionBankService()
