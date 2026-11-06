import os
import re
import io
import html
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
    from xhtml2pdf import pisa
except ImportError:
    pisa = None

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

        # Deduplicate identical sessions if identical rounds exist across consolidated and standalone files
        seen_sessions = set()
        deduped_sessions = []
        for s in sessions_list:
            r_name = s.get("rounds", [{}])[0].get("round_name", "") if s.get("rounds") else ""
            key = (s.get("company_name", "").lower(), r_name.lower(), s.get("latest_date", ""))
            if key in seen_sessions:
                continue
            seen_sessions.add(key)
            deduped_sessions.append(s)
        sessions_list = deduped_sessions

        companies_list = [s for s in sessions_list if s.get("total_questions", 0) > 0]

        # Recompute category counts from finalized deduplicated sessions
        recomputed_counts: Dict[str, int] = {}
        for c in companies_list:
            for r in c.get("rounds", []):
                for q in r.get("questions", []):
                    q_cat = q.get("category", "General")
                    recomputed_counts[q_cat] = recomputed_counts.get(q_cat, 0) + 1
                    if q.get("is_nagaraj"):
                        recomputed_counts["Nagaraj's Interview"] = recomputed_counts.get("Nagaraj's Interview", 0) + 1
        category_counts = recomputed_counts

        # Finalize rounds list & categories and populate calendar events
        r_counter = 1
        for c in companies_list:
            c["categories"] = sorted(list(c["categories"]))
            for r in c.get("rounds", []):
                clean_c = re.sub(r'[^a-zA-Z0-9]', '_', c.get("company_name", "")).strip('_').lower()
                clean_r = re.sub(r'[^a-zA-Z0-9]', '_', r.get("round_name", "")).strip('_').lower()
                r["round_id"] = f"rnd_{clean_c}_{clean_r}_{r_counter}"
                r_counter += 1
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

    def get_round(
        self,
        round_id: Optional[str] = None,
        company_name: Optional[str] = None,
        round_name: Optional[str] = None,
        round_date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Look up a round across all companies by round_id or company + round name."""
        data = self.get_data()
        clean_comp = company_name.strip().lower() if company_name else None
        clean_round = round_name.strip().lower() if round_name else None
        clean_date = round_date.strip().lower() if round_date else None

        for comp in data.get("companies", []):
            if clean_comp and comp.get("company_name", "").strip().lower() != clean_comp:
                continue
            for r in comp.get("rounds", []):
                if round_id and r.get("round_id") == round_id:
                    res = dict(r)
                    res["company_name"] = comp.get("company_name")
                    res["is_nagaraj_interview"] = comp.get("is_nagaraj_interview", False)
                    return res
                if clean_round and r.get("round_name", "").strip().lower() == clean_round:
                    if not clean_date or r.get("date", "").strip().lower() == clean_date:
                        res = dict(r)
                        res["company_name"] = comp.get("company_name")
                        res["is_nagaraj_interview"] = comp.get("is_nagaraj_interview", False)
                        return res
        return None

    def get_company(self, company_name: str) -> Optional[Dict[str, Any]]:
        """Look up a company by name."""
        data = self.get_data()
        target = company_name.strip().lower()
        for comp in data.get("companies", []):
            if comp.get("company_name", "").strip().lower() == target:
                return comp
        return None

    def generate_round_markdown(self, round_info: Dict[str, Any]) -> str:
        """Format a round and all its questions into a clean Markdown string."""
        comp_name = round_info.get("company_name", "Company")
        round_name = round_info.get("round_name", "Interview Round")
        round_date = round_info.get("date", "Recent")
        questions = round_info.get("questions", [])
        categories = round_info.get("categories", [])
        is_nagaraj = round_info.get("is_nagaraj_interview", False)
        answered_q = sum(1 for q in questions if q.get("has_answer"))

        lines = [
            f"# DevOps Interview Questions: {comp_name} - {round_name}",
            "",
            f"- **Company:** {comp_name}",
            f"- **Round:** {round_name}",
            f"- **Date:** {round_date}",
            f"- **Total Questions:** {len(questions)} ({answered_q} with Production Answers)",
        ]
        if categories:
            lines.append(f"- **Categories:** {', '.join(categories)}")
        if is_nagaraj:
            lines.append("- **Special Marker:** Nagaraj's Verified Interview")
        lines.extend([
            "- **Source:** DevOps Knowledge Portal & Interview Hub",
            "",
            "---",
            ""
        ])

        for idx, q in enumerate(questions, 1):
            q_text = q.get("question", "").strip()
            cat = q.get("category", "General")
            ans_text = q.get("answer", "").strip()
            has_ans = q.get("has_answer", False)
            is_sub = q.get("is_sub_q", False)

            prefix = "↳ Follow-up: " if is_sub else ""
            lines.append(f"### Q{idx}. {prefix}{q_text}")
            lines.append(f"*Category: {cat}*")
            lines.append("")

            if has_ans and ans_text:
                lines.append("#### Verified Production Answer:")
                lines.append(ans_text)
            else:
                lines.append("*Status: Question only (No answer recorded).*")

            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def generate_company_markdown(self, comp: Dict[str, Any]) -> str:
        """Format all rounds of a company into a comprehensive Markdown document."""
        comp_name = comp.get("company_name", "Company")
        rounds = comp.get("rounds", [])
        total_q = comp.get("total_questions", 0)
        categories = comp.get("categories", [])
        latest_date = comp.get("latest_date", "Recent")
        is_nagaraj = comp.get("is_nagaraj_interview", False)

        lines = [
            f"# DevOps Interview Questions: {comp_name}",
            "",
            f"- **Company:** {comp_name}",
            f"- **Total Rounds:** {len(rounds)}",
            f"- **Total Questions:** {total_q}",
            f"- **Latest Interview Date:** {latest_date}",
        ]
        if categories:
            lines.append(f"- **Categories Covered:** {', '.join(categories)}")
        if is_nagaraj:
            lines.append("- **Special Marker:** Nagaraj's Verified Interview")
        lines.extend([
            "- **Source:** DevOps Knowledge Portal & Interview Hub",
            "",
            "---",
            ""
        ])

        for r_idx, r in enumerate(rounds, 1):
            r_name = r.get("round_name", f"Round {r_idx}")
            r_date = r.get("date", "Recent")
            questions = r.get("questions", [])
            r_answered = sum(1 for q in questions if q.get("has_answer"))

            lines.append(f"## {r_idx}. {r_name} ({r_date})")
            lines.append(f"**Total Questions:** {len(questions)} ({r_answered} with Production Answers)")
            lines.append("")

            for q_idx, q in enumerate(questions, 1):
                q_text = q.get("question", "").strip()
                cat = q.get("category", "General")
                ans_text = q.get("answer", "").strip()
                has_ans = q.get("has_answer", False)
                is_sub = q.get("is_sub_q", False)

                prefix = "↳ Follow-up: " if is_sub else ""
                lines.append(f"### Q{q_idx}. {prefix}{q_text}")
                lines.append(f"*Category: {cat}*")
                lines.append("")

                if has_ans and ans_text:
                    lines.append("#### Verified Production Answer:")
                    lines.append(ans_text)
                else:
                    lines.append("*Status: Question only (No answer recorded).*")

                lines.append("")
                lines.append("---")
                lines.append("")

        return "\n".join(lines)

    def generate_round_html(self, round_info: Dict[str, Any]) -> str:
        """Format a round and all its questions into preview-mode HTML for PDF rendering."""
        comp_name = round_info.get("company_name", "Company")
        round_name = round_info.get("round_name", "Interview Round")
        round_date = round_info.get("date", "Recent")
        questions = round_info.get("questions", [])
        categories = round_info.get("categories", [])
        is_nagaraj = round_info.get("is_nagaraj_interview", False)
        total_q = len(questions)
        answered_q = sum(1 for q in questions if q.get("has_answer"))

        q_cards = []
        for idx, q in enumerate(questions, 1):
            q_text = html.escape(q.get("question", "").strip())
            cat = q.get("category", "General")
            is_sub = q.get("is_sub_q", False)
            ans_html = q.get("answer_html", "") or render_md(q.get("answer", ""))
            ans_html = ans_html.replace("↳", "- ").replace("●", "&bull;").replace("🏢", "").replace("📁", "")

            sub_tag = '<span class="sub-tag">Follow-up</span>' if is_sub else ""
            cat_tag = f'<span class="cat-tag">{html.escape(cat)}</span>' if cat else ""

            if ans_html.strip():
                ans_block = f'''
                <div class="ans-box">
                    <div class="ans-label">Verified Production Answer</div>
                    <div class="ans-body">{ans_html}</div>
                </div>
                '''
            else:
                ans_block = '''
                <div class="ans-box no-ans">
                    <div class="ans-label-muted">Status: Question only (No answer recorded).</div>
                </div>
                '''

            q_cards.append(f'''
            <div class="q-card">
                <div class="q-header">
                    <span class="q-num">Q{idx}</span>
                    {sub_tag}
                    {cat_tag}
                    <span class="q-text">{q_text}</span>
                </div>
                {ans_block}
            </div>
            ''')

        css = """
        @page {
            size: A4 portrait;
            margin: 1.4cm 1.2cm 1.4cm 1.2cm;
            @bottom-right {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 8pt;
                color: #64748b;
                font-family: Helvetica, Arial, sans-serif;
            }
            @bottom-left {
                content: "DevOps Interview Hub • Question Bank";
                font-size: 8pt;
                color: #94a3b8;
                font-family: Helvetica, Arial, sans-serif;
            }
        }
        body {
            font-family: Helvetica, Arial, sans-serif;
            font-size: 9.5pt;
            line-height: 1.5;
            color: #1e293b;
        }
        .header-box {
            border-bottom: 2px solid #4f46e5;
            padding-bottom: 8px;
            margin-bottom: 12px;
        }
        .title {
            font-size: 15pt;
            font-weight: bold;
            color: #0f172a;
            margin: 0 0 3px 0;
        }
        .subtitle {
            font-size: 8.5pt;
            color: #64748b;
            margin: 0;
        }
        .meta-bar {
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            padding: 6px 10px;
            border-radius: 4px;
            margin-bottom: 14px;
            font-size: 8.5pt;
            color: #334155;
        }
        .meta-item {
            margin-right: 14px;
        }
        .q-card {
            margin-bottom: 12px;
            border: 1px solid #e2e8f0;
            border-radius: 5px;
            background-color: #ffffff;
            page-break-inside: avoid;
        }
        .q-header {
            padding: 7px 10px;
            background-color: #f8fafc;
            border-bottom: 1px solid #e2e8f0;
            font-size: 9.5pt;
            font-weight: bold;
            color: #0f172a;
        }
        .q-num {
            background-color: #4f46e5;
            color: #ffffff;
            padding: 1px 5px;
            border-radius: 3px;
            font-size: 7.5pt;
            margin-right: 5px;
        }
        .cat-tag {
            background-color: #ecfdf5;
            color: #059669;
            border: 1px solid #a7f3d0;
            padding: 1px 5px;
            border-radius: 3px;
            font-size: 7pt;
            margin-right: 5px;
        }
        .sub-tag {
            background-color: #fef3c7;
            color: #b45309;
            border: 1px solid #fde68a;
            padding: 1px 4px;
            border-radius: 3px;
            font-size: 7pt;
            margin-right: 5px;
        }
        .ans-box {
            padding: 7px 10px;
            background-color: #ffffff;
        }
        .ans-box.no-ans {
            background-color: #fcfcfc;
        }
        .ans-label {
            font-size: 7.5pt;
            font-weight: bold;
            color: #059669;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 3px;
        }
        .ans-label-muted {
            font-size: 8pt;
            color: #64748b;
            font-style: italic;
        }
        .ans-body {
            font-size: 8.8pt;
            color: #334155;
        }
        pre, code {
            font-family: Courier, monospace;
            font-size: 7.5pt;
            background-color: #f1f5f9;
            color: #0f172a;
        }
        pre {
            padding: 5px 8px;
            border: 1px solid #cbd5e1;
            border-radius: 3px;
            margin: 4px 0;
        }
        ul, ol {
            margin: 3px 0 3px 14px;
            padding: 0;
        }
        li {
            margin-bottom: 2px;
        }
        """

        categories_str = ", ".join(categories) if categories else "All DevOps Topics"

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{html.escape(comp_name)} - {html.escape(round_name)}</title>
<style>{css}</style>
</head>
<body>
    <div class="header-box">
        <div class="title">{html.escape(comp_name)} &bull; {html.escape(round_name)}</div>
        <div class="subtitle">DevOps Interview Questions &amp; Production Verified Answers</div>
    </div>
    <div class="meta-bar">
        <span class="meta-item"><strong>Date:</strong> {html.escape(round_date)}</span>
        <span class="meta-item"><strong>Total Questions:</strong> {total_q} ({answered_q} with Verified Answers)</span>
        <span class="meta-item"><strong>Categories:</strong> {html.escape(categories_str)}</span>
        {f'<span class="meta-item" style="color:#b45309;"><strong>Verified:</strong> Nagaraj Interview</span>' if is_nagaraj else ''}
    </div>
    {''.join(q_cards)}
</body>
</html>"""

    def generate_round_pdf(self, round_info: Dict[str, Any]) -> bytes:
        """Convert round HTML into a PDF byte stream."""
        html_str = self.generate_round_html(round_info)
        buf = io.BytesIO()
        if pisa:
            pisa.CreatePDF(html_str, dest=buf)
        return buf.getvalue()

    def generate_company_html(self, comp: Dict[str, Any]) -> str:
        """Format a company's full interview rounds into preview-mode HTML for PDF rendering."""
        comp_name = comp.get("company_name", "Company")
        rounds = comp.get("rounds", [])
        total_q = comp.get("total_questions", 0)
        categories = comp.get("categories", [])
        latest_date = comp.get("latest_date", "Recent")
        is_nagaraj = comp.get("is_nagaraj_interview", False)

        round_sections = []
        for r_idx, r in enumerate(rounds, 1):
            r_name = r.get("round_name", f"Round {r_idx}")
            r_date = r.get("date", "Recent")
            questions = r.get("questions", [])

            q_cards = []
            for idx, q in enumerate(questions, 1):
                q_text = html.escape(q.get("question", "").strip())
                cat = q.get("category", "General")
                is_sub = q.get("is_sub_q", False)
                ans_html = q.get("answer_html", "") or render_md(q.get("answer", ""))
                ans_html = ans_html.replace("↳", "- ").replace("●", "&bull;").replace("🏢", "").replace("📁", "")

                sub_tag = '<span class="sub-tag">Follow-up</span>' if is_sub else ""
                cat_tag = f'<span class="cat-tag">{html.escape(cat)}</span>' if cat else ""

                if ans_html.strip():
                    ans_block = f'''
                    <div class="ans-box">
                        <div class="ans-label">Verified Production Answer</div>
                        <div class="ans-body">{ans_html}</div>
                    </div>
                    '''
                else:
                    ans_block = '''
                    <div class="ans-box no-ans">
                        <div class="ans-label-muted">Status: Question only (No answer recorded).</div>
                    </div>
                    '''

                q_cards.append(f'''
                <div class="q-card">
                    <div class="q-header">
                        <span class="q-num">Q{idx}</span>
                        {sub_tag}
                        {cat_tag}
                        <span class="q-text">{q_text}</span>
                    </div>
                    {ans_block}
                </div>
                ''')

            round_sections.append(f'''
            <div class="round-section" style="page-break-before: auto; margin-top: 16px;">
                <div class="section-title">{r_idx}. {html.escape(r_name)} ({html.escape(r_date)}) &bull; {len(questions)} Questions</div>
                {''.join(q_cards)}
            </div>
            ''')

        css = """
        @page {
            size: A4 portrait;
            margin: 1.4cm 1.2cm 1.4cm 1.2cm;
            @bottom-right {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 8pt;
                color: #64748b;
                font-family: Helvetica, Arial, sans-serif;
            }
            @bottom-left {
                content: "DevOps Interview Hub • Company Archive";
                font-size: 8pt;
                color: #94a3b8;
                font-family: Helvetica, Arial, sans-serif;
            }
        }
        body {
            font-family: Helvetica, Arial, sans-serif;
            font-size: 9.5pt;
            line-height: 1.5;
            color: #1e293b;
        }
        .header-box {
            border-bottom: 2px solid #4f46e5;
            padding-bottom: 8px;
            margin-bottom: 12px;
        }
        .title {
            font-size: 16pt;
            font-weight: bold;
            color: #0f172a;
            margin: 0 0 3px 0;
        }
        .subtitle {
            font-size: 8.5pt;
            color: #64748b;
            margin: 0;
        }
        .meta-bar {
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            padding: 6px 10px;
            border-radius: 4px;
            margin-bottom: 14px;
            font-size: 8.5pt;
            color: #334155;
        }
        .meta-item {
            margin-right: 14px;
        }
        .section-title {
            font-size: 12pt;
            font-weight: bold;
            color: #312e81;
            background-color: #eef2ff;
            border-left: 4px solid #4f46e5;
            padding: 5px 8px;
            margin-bottom: 10px;
        }
        .q-card {
            margin-bottom: 12px;
            border: 1px solid #e2e8f0;
            border-radius: 5px;
            background-color: #ffffff;
            page-break-inside: avoid;
        }
        .q-header {
            padding: 7px 10px;
            background-color: #f8fafc;
            border-bottom: 1px solid #e2e8f0;
            font-size: 9.5pt;
            font-weight: bold;
            color: #0f172a;
        }
        .q-num {
            background-color: #4f46e5;
            color: #ffffff;
            padding: 1px 5px;
            border-radius: 3px;
            font-size: 7.5pt;
            margin-right: 5px;
        }
        .cat-tag {
            background-color: #ecfdf5;
            color: #059669;
            border: 1px solid #a7f3d0;
            padding: 1px 5px;
            border-radius: 3px;
            font-size: 7pt;
            margin-right: 5px;
        }
        .sub-tag {
            background-color: #fef3c7;
            color: #b45309;
            border: 1px solid #fde68a;
            padding: 1px 4px;
            border-radius: 3px;
            font-size: 7pt;
            margin-right: 5px;
        }
        .ans-box {
            padding: 7px 10px;
            background-color: #ffffff;
        }
        .ans-box.no-ans {
            background-color: #fcfcfc;
        }
        .ans-label {
            font-size: 7.5pt;
            font-weight: bold;
            color: #059669;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 3px;
        }
        .ans-label-muted {
            font-size: 8pt;
            color: #64748b;
            font-style: italic;
        }
        .ans-body {
            font-size: 8.8pt;
            color: #334155;
        }
        pre, code {
            font-family: Courier, monospace;
            font-size: 7.5pt;
            background-color: #f1f5f9;
            color: #0f172a;
        }
        pre {
            padding: 5px 8px;
            border: 1px solid #cbd5e1;
            border-radius: 3px;
            margin: 4px 0;
        }
        ul, ol {
            margin: 3px 0 3px 14px;
            padding: 0;
        }
        li {
            margin-bottom: 2px;
        }
        """

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>All Rounds: {html.escape(comp_name)}</title>
<style>{css}</style>
</head>
<body>
    <div class="header-box">
        <div class="title">{html.escape(comp_name)} &bull; All Interview Rounds</div>
        <div class="subtitle">Complete Questions &amp; Verified Production Answers</div>
    </div>
    <div class="meta-bar">
        <span class="meta-item"><strong>Company:</strong> {html.escape(comp_name)}</span>
        <span class="meta-item"><strong>Total Rounds:</strong> {len(rounds)}</span>
        <span class="meta-item"><strong>Total Questions:</strong> {total_q}</span>
        <span class="meta-item"><strong>Latest Date:</strong> {html.escape(latest_date)}</span>
    </div>
    {''.join(round_sections)}
</body>
</html>"""

    def generate_company_pdf(self, comp: Dict[str, Any]) -> bytes:
        """Convert company HTML into a PDF byte stream."""
        html_str = self.generate_company_html(comp)
        buf = io.BytesIO()
        if pisa:
            pisa.CreatePDF(html_str, dest=buf)
        return buf.getvalue()

question_bank_service = QuestionBankService()
