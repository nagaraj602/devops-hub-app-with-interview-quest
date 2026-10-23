import os
import re
import pickle
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from app.config import QA_SESSIONS_DIR

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

MONTH_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'june': 6, 'jul': 7, 'july': 7, 'aug': 8, 'sep': 9, 'oct': 10,
    'nov': 11, 'dec': 12
}

def parse_date_ts(d_str: str) -> float:
    if not d_str:
        return 0.0
    m = re.search(r'(\d{1,2})-([A-Za-z]+)-(\d{4})', d_str)
    if m:
        day = int(m.group(1))
        mon_str = m.group(2).lower()[:4]
        month = MONTH_MAP.get(mon_str, 1)
        year = int(m.group(3))
        try:
            return datetime(year, month, day).timestamp()
        except Exception:
            return 0.0
    return 0.0

def clean_grammar_and_unescape(text: str) -> str:
    if not text:
        return ""
    t = text.replace(r'\.', '.').replace(r'\_', '_').replace(r'\[', '[').replace(r'\]', ']').replace(r'\*', '*').replace(r'\-', '-')
    t = re.sub(r'\bpassword less\b', 'passwordless', t, flags=re.I)
    t = re.sub(r'Istn\'t it the either way', "Isn't it the other way", t, flags=re.I)
    t = re.sub(r'\bistructor\b', 'instructor', t, flags=re.I)
    t = re.sub(r'\bseperately\b', 'separately', t, flags=re.I)
    t = re.sub(r'\bfuctionality\b', 'functionality', t, flags=re.I)
    return t.strip()

def clean_question_text(q: str) -> str:
    if not q:
        return ""
    t = q.strip()
    if (t.startswith('**') and t.endswith('**')) or (t.startswith('*') and t.endswith('*')):
        t = t.strip('*').strip()
    # Strip leading Question / Sub-Question / Primary Question markers
    t = re.sub(r'^(?:\*|_)?\s*(?:\*\*)?(?:Primary Question|Sub-Question(?:\s*\d+)?(?:/[A-Za-z]+)?|Main Question|Scenario Question|Question(?:\s*\d+)?)(?:\s*\(.*?\))?:?\s*(?:\*\*)?\s*(?:\*|_)?[:\s\-–—]*', '', t, flags=re.I)
    t = re.sub(r'^(?:\*\*)?Q(?:uestion)?(?:\s*\d+)?:?\s*(?:\*\*)?[:\s\-–—]*', '', t, flags=re.I)
    t = t.strip('*_ \t:\"\'')
    return t

def is_none_provided(text: str) -> bool:
    if not text:
        return True
    # Strip leading header like * **Instructor's Answer / Suggestion:**
    t = re.sub(r'^[\s*\-_#]*(?:\*\*)?[^:\n]+(?:\*\*)?[:\-–—]\s*', '', text, flags=re.I).strip()
    t_clean = t.lower().strip('*_ \t.:\"\'')
    if not t_clean or t_clean in (
        'none provided', 'none provided.',
        'none provided in the transcript', 'none provided in the transcript.',
        'none provided (instructed student to review and prepare)',
        'none provided (instructed student to review and prepare).',
        'none', 'n/a'
    ):
        return True
    return False

def is_answer_start(s: str) -> bool:
    t = s.strip()
    if not t:
        return False
    cleaned = re.sub(r'^[\*\-\#\s]+', '', t).strip()
    if re.match(r'^(?:Question|Candidate|Sub-Question|Primary Question|Main Question|Topic|\d+\.|\d+\))', cleaned, re.I):
        return False

    ans_keywords = [
        'guidance / expected answer', 'guidance/expected answer', 'expected answer',
        'instructor\'s guidance', 'instructor guidance', 'interviewer guidance',
        'instructor\'s suggestion', 'instructor suggestion', 'suggestion/answer provided',
        'instructor\'s answer', 'instructor answer', 'instructor\'s answers',
        'instructor\'s addition', 'instructor\'s affirmation',
        'suggested answer / guidance', 'suggested answer',
        'answer provided by instructor', 'answer & suggestion provided by instructor',
        'answer/suggestion', 'answer / suggestion',
        'technical guidance & instructor solution', 'technical guidance & best practice',
        'technical explanation & solution', 'technical answer & guidance',
        'technical guidance', 'technical explanation',
        'core technical answer', 'model answer', 'scenario resolution',
        'recommended solution', 'proper solutions',
        'preventing alert fatigue (instructor guidance)',
        'standards established by the instructor',
        'instructor answers provided to student queries',
        'instructor guidance provided', 'instructor guidance & recommendations',
        'instructor guidance & provided model answer'
    ]
    cl = cleaned.lower().strip('*_ ')
    for kw in ans_keywords:
        if cl.startswith(kw):
            return True

    if re.match(r'^(?:\*\*)?(?:Ans|Answer|Suggestion)(?:\*\*)?\s*:\s*', cleaned, re.I):
        return True
    if re.match(r'^\*Ans\*:\s*', cleaned, re.I):
        return True

    return False

def is_valid_answer_text(text: str) -> bool:
    if not text:
        return False
    t = text.strip()
    if len(t) < 4:
        return False
    if is_none_provided(t):
        return False
    if re.match(r'^(?:\*\*)?(?:Question(?:\s*\d+)?|Candidate(?:\s*\d+)?|Topic(?:\s*\d+)?)(?:\*\*)?$', t, re.I):
        return False
    return True

INSTRUCTORS_CONFIG = [
    {
        "id": "hitish",
        "name": "Hitish",
        "filename": "4.1. Hitish QA 59 to 87 class.md",
        "classes": "Class 59 to 87",
        "avatar_text": "HI",
        "avatar_bg": "#eff6ff",
        "avatar_color": "#2563eb",
        "order": 1
    },
    {
        "id": "sai",
        "name": "Sai",
        "filename": "6. Sai QA 81 & 83 class.md",
        "classes": "Class 81 & 83 (Mock)",
        "avatar_text": "SA",
        "avatar_bg": "#f5f3ff",
        "avatar_color": "#7c3aed",
        "order": 2
    },
    {
        "id": "aditya",
        "name": "Aditya",
        "filename": "5. Aditya QA 69 & 77 class.md",
        "classes": "Class 69 & 77",
        "avatar_text": "AD",
        "avatar_bg": "#ecfdf5",
        "avatar_color": "#059669",
        "order": 3
    },
    {
        "id": "zubair",
        "name": "Zubair",
        "filename": "3. Zubair QA 53 class.md",
        "classes": "Class 53",
        "avatar_text": "ZU",
        "avatar_bg": "#fffbeb",
        "avatar_color": "#d97706",
        "order": 4
    },
    {
        "id": "roopa",
        "name": "Roopa",
        "filename": "2.1. Roopa QA 22 class.md",
        "classes": "Class 22",
        "avatar_text": "RO",
        "avatar_bg": "#fdf2f8",
        "avatar_color": "#db2777",
        "order": 5
    },
    {
        "id": "krishna",
        "name": "Krishna",
        "filename": "1.1. Krishna QA 1 to 8 class.md",
        "classes": "Class 1 to 8",
        "avatar_text": "KR",
        "avatar_bg": "#e0f2fe",
        "avatar_color": "#0284c7",
        "order": 6
    },
    {
        "id": "topics",
        "name": "General Topics (Archive)",
        "filename": "0. Without instructor name, categorized with topics.md",
        "classes": "Core Curriculum (Topics)",
        "avatar_text": "QA",
        "avatar_bg": "#f1f5f9",
        "avatar_color": "#475569",
        "order": 7
    }
]

class QAService:
    def __init__(self, qa_dir: Optional[str] = None):
        self.dir_path = qa_dir or QA_SESSIONS_DIR
        self._cache: Optional[Dict[str, Any]] = None
        self._on_refresh_callbacks: List[Callable[[], None]] = []

    def add_on_refresh_callback(self, cb: Callable[[], None]):
        self._on_refresh_callbacks.append(cb)

    def _get_cache_path(self) -> str:
        return os.path.join(self.dir_path, ".cache_qa.pkl")

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

        instructors_data = []
        total_questions = 0
        total_sessions = 0
        total_answered = 0

        for config in INSTRUCTORS_CONFIG:
            fpath = os.path.join(self.dir_path, config["filename"])
            if not os.path.exists(fpath):
                fallback = os.path.join("content", "repos", "notes", "ArtisanTek QA Sessions", config["filename"])
                if os.path.exists(fallback):
                    fpath = fallback

            if not os.path.exists(fpath):
                continue

            with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                raw_content = fp.read()

            inst_obj = self._parse_instructor_file(config, raw_content)
            if inst_obj and inst_obj.get("total_questions", 0) > 0:
                instructors_data.append(inst_obj)
                total_questions += inst_obj["total_questions"]
                total_sessions += len(inst_obj["sessions"])
                for s in inst_obj["sessions"]:
                    total_answered += sum(1 for q in s.get("questions", []) if q.get("has_answer"))

        # Order instructors strictly: Hitish -> Sai -> Aditya -> Zubair -> Roopa -> Krishna -> General Topics
        instructors_data.sort(key=lambda x: x.get("order", 99))

        instructor_pills = [{"id": "All", "name": "All", "count": total_questions}]
        for inst in instructors_data:
            instructor_pills.append({
                "id": inst["id"],
                "name": inst["name"],
                "count": inst["total_questions"]
            })

        self._cache = {
            "instructors": instructors_data,
            "stats": {
                "total_questions": total_questions,
                "total_instructors": len(instructors_data),
                "total_sessions": total_sessions,
                "answered_questions": total_answered,
                "questions_only": total_questions - total_answered
            },
            "instructor_pills": instructor_pills
        }

        try:
            with open(cache_path, "wb") as cpf:
                pickle.dump({"fingerprint": fingerprint, "data": self._cache}, cpf, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception:
            pass

        return self._cache

    def _parse_instructor_file(self, config: Dict[str, Any], content: str) -> Dict[str, Any]:
        inst_id = config["id"]
        if inst_id == "hitish":
            return self._parse_hitish(config, content)
        elif inst_id == "sai":
            return self._parse_sai(config, content)
        elif inst_id == "aditya":
            return self._parse_aditya(config, content)
        elif inst_id == "zubair":
            return self._parse_zubair(config, content)
        elif inst_id == "roopa":
            return self._parse_roopa(config, content)
        elif inst_id == "krishna":
            return self._parse_krishna(config, content)
        elif inst_id == "topics":
            return self._parse_topics(config, content)
        return {}

    def _parse_hitish(self, config: Dict[str, Any], content: str) -> Dict[str, Any]:
        lines = content.splitlines()
        sessions = []
        curr_date = "General"
        curr_qs = []
        curr_q = ""
        curr_ans = []
        in_ans = False
        curr_block_qs = []
        q_idx = 1

        def push_q():
            nonlocal curr_q, q_idx, curr_qs, curr_block_qs
            q_clean = clean_question_text(curr_q)
            if not q_clean:
                curr_q = ""
                return
            q_obj = {
                "id": f"qa_hitish_{q_idx}",
                "question": q_clean,
                "answer": "",
                "answer_html": "",
                "has_answer": False,
                "instructor": config["name"],
                "session_date": curr_date
            }
            q_idx += 1
            curr_qs.append(q_obj)
            curr_block_qs.append(q_obj)
            curr_q = ""

        def apply_block_ans():
            nonlocal curr_ans, in_ans, curr_block_qs
            ans_raw = "\n".join(curr_ans).strip()
            ans_clean = clean_grammar_and_unescape(ans_raw)
            has_ans = is_valid_answer_text(ans_clean)
            if has_ans:
                ans_html = render_md(ans_clean)
                for q_obj in curr_block_qs:
                    if not q_obj["has_answer"]:
                        q_obj["answer"] = ans_clean
                        q_obj["answer_html"] = ans_html
                        q_obj["has_answer"] = True
            curr_ans = []
            in_ans = False
            curr_block_qs = []

        def push_session():
            nonlocal curr_qs, curr_date, sessions
            push_q()
            apply_block_ans()
            if curr_qs:
                sessions.append({
                    "session_id": f"hitish_{curr_date.replace('-', '_')}",
                    "session_name": curr_date,
                    "date": curr_date,
                    "timestamp": parse_date_ts(curr_date),
                    "questions": list(curr_qs),
                    "total_questions": len(curr_qs)
                })
                curr_qs = []

        for line in lines:
            s = clean_grammar_and_unescape(line)
            if not s:
                if in_ans:
                    curr_ans.append("")
                continue

            m_d = re.match(r'^##\s*([0-9]{1,2}-[A-Za-z]+-[0-9]{4}):?', s)
            if m_d:
                push_session()
                curr_date = m_d.group(1).strip()
                continue

            if is_answer_start(s):
                push_q()
                in_ans = True
                curr_ans.append(s)
                continue

            if s.startswith('**Question') or s.startswith('### '):
                push_q()
                apply_block_ans()
                continue

            m_q = re.match(r'^(?:\d+[\.\)]|\*\*\*\d+[\.\)]\*\*\*|\*\*\d+[\.\)]\*\*|Q:|\*\*Q:\*\*|\*\s*\*\*Question(?:\s*\d+)?(?:\s*\(.*?\))?:\*\*|\*\s*\*\*Main Question:\*\*|\*\s*\*\*Primary Question(?:s)?:\*\*|\*\s*\*\*Sub-Question(?:\s*\d+)?:\*\*|\*\*Question(?:\s*\d+)?(?:\s*\(.*?\))?:\*\*)\s*(.*)', s, re.I)
            is_bullet_q = s.startswith('* ') and not is_answer_start(s) and ('?' in s or any(w in s for w in ['Explain', 'Describe', 'What', 'How', 'Why']))

            if m_q and len(m_q.group(1).strip()) > 3:
                if in_ans:
                    apply_block_ans()
                push_q()
                curr_q = m_q.group(1).strip()
            elif is_bullet_q:
                if in_ans:
                    apply_block_ans()
                push_q()
                curr_q = s[2:].strip()
            elif in_ans:
                curr_ans.append(s)

        push_session()
        sessions.sort(key=lambda s: s.get("timestamp", 0.0), reverse=True)
        total_q = sum(s["total_questions"] for s in sessions)
        latest_d = sessions[0]["date"] if sessions else "Recent"

        return {
            "id": config["id"],
            "name": config["name"],
            "classes": config["classes"],
            "avatar_text": config["avatar_text"],
            "avatar_bg": config["avatar_bg"],
            "avatar_color": config["avatar_color"],
            "order": config["order"],
            "latest_date": latest_d,
            "total_questions": total_q,
            "sessions": sessions
        }

    def _parse_sai(self, config: Dict[str, Any], content: str) -> Dict[str, Any]:
        lines = content.splitlines()
        sessions = []
        curr_date = "2-Oct-2026"
        curr_qs = []
        curr_q = ""
        curr_ans = []
        in_ans = False
        curr_block_qs = []
        q_idx = 1

        def push_q():
            nonlocal curr_q, q_idx, curr_qs, curr_block_qs
            q_clean = clean_question_text(curr_q)
            if not q_clean:
                curr_q = ""
                return
            q_obj = {
                "id": f"qa_sai_{q_idx}",
                "question": q_clean,
                "answer": "",
                "answer_html": "",
                "has_answer": False,
                "instructor": config["name"],
                "session_date": curr_date
            }
            q_idx += 1
            curr_qs.append(q_obj)
            curr_block_qs.append(q_obj)
            curr_q = ""

        def apply_block_ans():
            nonlocal curr_ans, in_ans, curr_block_qs
            ans_raw = "\n".join(curr_ans).strip()
            ans_clean = clean_grammar_and_unescape(ans_raw)
            has_ans = is_valid_answer_text(ans_clean)
            if has_ans:
                ans_html = render_md(ans_clean)
                for q_obj in curr_block_qs:
                    if not q_obj["has_answer"]:
                        q_obj["answer"] = ans_clean
                        q_obj["answer_html"] = ans_html
                        q_obj["has_answer"] = True
            curr_ans = []
            in_ans = False
            curr_block_qs = []

        def push_session():
            nonlocal curr_qs, curr_date, sessions
            push_q()
            apply_block_ans()
            if curr_qs:
                sessions.append({
                    "session_id": f"sai_{curr_date.replace('-', '_')}",
                    "session_name": f"QA {curr_date}",
                    "date": curr_date,
                    "timestamp": parse_date_ts(curr_date),
                    "questions": list(curr_qs),
                    "total_questions": len(curr_qs)
                })
                curr_qs = []

        for line in lines:
            s = clean_grammar_and_unescape(line)
            if not s:
                if in_ans:
                    curr_ans.append("")
                continue

            m_d = re.search(r'(\d{1,2}-[A-Za-z]+-\d{4})', s)
            if s.startswith('##') and m_d:
                push_session()
                curr_date = m_d.group(1).strip()
                continue

            if is_answer_start(s):
                push_q()
                in_ans = True
                curr_ans.append(s)
                continue

            if re.match(r'^(?:#|##|\*\*\d+\.|\d+\.)', s) and not any(w in s for w in ['Primary', 'Question', 'Sub-Question', 'Scenario']):
                push_q()
                apply_block_ans()
                continue

            m_q = re.match(r'^\*\s*(?:\*\*(?:Primary Question|Sub-Question \d+|Sub-Questions|Scenario Question):\*\*\s*)?(.*)', s)
            if 'Primary Question' in s or 'Sub-Question' in s or 'Scenario Question' in s:
                if in_ans:
                    apply_block_ans()
                push_q()
                curr_q = m_q.group(1).strip().strip('"\'') if m_q else s
            elif s.startswith('* ') and not in_ans and ('?' in s or any(w in s for w in ['Explain', 'Describe', 'What', 'How', 'Why'])):
                if in_ans:
                    apply_block_ans()
                push_q()
                curr_q = s[2:].strip().strip('"\'')
            elif in_ans:
                curr_ans.append(s)

        push_session()
        sessions.sort(key=lambda s: s.get("timestamp", 0.0), reverse=True)
        total_q = sum(s["total_questions"] for s in sessions)

        return {
            "id": config["id"],
            "name": config["name"],
            "classes": config["classes"],
            "avatar_text": config["avatar_text"],
            "avatar_bg": config["avatar_bg"],
            "avatar_color": config["avatar_color"],
            "order": config["order"],
            "latest_date": sessions[0]["date"] if sessions else "Recent",
            "total_questions": total_q,
            "sessions": sessions
        }

    def _parse_aditya(self, config: Dict[str, Any], content: str) -> Dict[str, Any]:
        lines = content.splitlines()
        sessions = []
        curr_date = "18-Sep-2026"
        curr_qs = []
        curr_q = ""
        curr_topic = ""
        q_idx = 1

        def push_q():
            nonlocal curr_q, q_idx, curr_topic
            q_clean = clean_question_text(curr_q)
            if not q_clean:
                curr_q = ""
                return
            # Aditya QA consists of rapid questions without provided solutions
            curr_qs.append({
                "id": f"qa_aditya_{q_idx}",
                "question": q_clean,
                "answer": "",
                "answer_html": "",
                "has_answer": False,
                "instructor": config["name"],
                "session_date": curr_date,
                "topic": curr_topic
            })
            q_idx += 1
            curr_q = ""

        def push_session():
            nonlocal curr_qs, curr_date
            push_q()
            if curr_qs:
                sessions.append({
                    "session_id": f"aditya_{curr_date.replace('-', '_')}",
                    "session_name": curr_date,
                    "date": curr_date,
                    "timestamp": parse_date_ts(curr_date),
                    "questions": list(curr_qs),
                    "total_questions": len(curr_qs)
                })
                curr_qs = []

        for line in lines:
            s = clean_grammar_and_unescape(line)
            if not s:
                continue

            m_d = re.match(r'^##\s*([0-9]{1,2}-[A-Za-z]+-[0-9]{4}):?', s)
            if m_d:
                push_session()
                curr_date = m_d.group(1).strip()
                continue

            if s.startswith("**") and s.endswith("**") and len(s) > 4:
                topic_title = s.strip('*').strip()
                if "Candidate" not in topic_title:
                    curr_topic = topic_title
                continue

            if s.startswith("* "):
                push_q()
                curr_q = s[2:].strip()

        push_session()
        sessions.sort(key=lambda s: s.get("timestamp", 0.0), reverse=True)
        total_q = sum(s["total_questions"] for s in sessions)

        return {
            "id": config["id"],
            "name": config["name"],
            "classes": config["classes"],
            "avatar_text": config["avatar_text"],
            "avatar_bg": config["avatar_bg"],
            "avatar_color": config["avatar_color"],
            "order": config["order"],
            "latest_date": sessions[0]["date"] if sessions else "Recent",
            "total_questions": total_q,
            "sessions": sessions
        }

    def _parse_zubair(self, config: Dict[str, Any], content: str) -> Dict[str, Any]:
        lines = content.splitlines()
        session_date = "2-June-2026"
        m_d = re.search(r'(\d{1,2}-[A-Za-z]+-\d{4})', content)
        if m_d:
            session_date = m_d.group(1)

        qs = []
        curr_q = ""
        curr_ans = []
        in_ans = False
        q_idx = 1

        def push_q():
            nonlocal curr_q, curr_ans, in_ans, q_idx
            q_clean = clean_question_text(curr_q)
            if not q_clean:
                curr_q = ""
                curr_ans = []
                in_ans = False
                return
            ans_clean = clean_grammar_and_unescape("\n".join(curr_ans)).strip()
            has_ans = is_valid_answer_text(ans_clean)
            qs.append({
                "id": f"qa_zubair_{q_idx}",
                "question": q_clean,
                "answer": ans_clean if has_ans else "",
                "answer_html": render_md(ans_clean) if has_ans else "",
                "has_answer": has_ans,
                "instructor": config["name"],
                "session_date": session_date
            })
            q_idx += 1
            curr_q = ""
            curr_ans = []
            in_ans = False

        for line in lines:
            s = clean_grammar_and_unescape(line)
            if not s:
                continue

            if s.startswith("* **Question:**"):
                push_q()
                curr_q = s.replace("* **Question:**", "").strip()
                in_ans = False
            elif s.startswith("* *Answer") or s.startswith("* *Suggestion:"):
                in_ans = True
                ans_text = re.sub(r'^\*\s*\*(?:Answer/Suggestion|Answer|Suggestion):\*\s*', '', s).strip()
                curr_ans.append(ans_text)
            elif in_ans and not s.startswith("#") and not s.startswith("###"):
                curr_ans.append(s)

        push_q()

        session_obj = {
            "session_id": "zubair_2_june_2026",
            "session_name": session_date,
            "date": session_date,
            "timestamp": parse_date_ts(session_date),
            "questions": qs,
            "total_questions": len(qs)
        }

        return {
            "id": config["id"],
            "name": config["name"],
            "classes": config["classes"],
            "avatar_text": config["avatar_text"],
            "avatar_bg": config["avatar_bg"],
            "avatar_color": config["avatar_color"],
            "order": config["order"],
            "latest_date": session_date,
            "total_questions": len(qs),
            "sessions": [session_obj]
        }

    def _parse_roopa(self, config: Dict[str, Any], content: str) -> Dict[str, Any]:
        lines = content.splitlines()
        session_date = "22-Mar-2026"
        m_d = re.search(r'(\d{1,2}-[A-Za-z]+-\d{4})', content)
        if m_d:
            session_date = m_d.group(1)

        qs = []
        curr_q = ""
        curr_ans = []
        in_ans = False
        q_idx = 1

        def push_q():
            nonlocal curr_q, curr_ans, in_ans, q_idx
            q_clean = clean_question_text(curr_q)
            if not q_clean:
                curr_q = ""
                curr_ans = []
                in_ans = False
                return
            ans_clean = clean_grammar_and_unescape("\n".join(curr_ans)).strip()
            ans_clean = re.sub(r'^\*\s*(?:\*\*Answer provided by Instructor:\*\*|\*\*Suggestion:\*\*|\*Suggestion:\*)\s*', '', ans_clean).strip()
            has_ans = is_valid_answer_text(ans_clean)
            qs.append({
                "id": f"qa_roopa_{q_idx}",
                "question": q_clean,
                "answer": ans_clean if has_ans else "",
                "answer_html": render_md(ans_clean) if has_ans else "",
                "has_answer": has_ans,
                "instructor": config["name"],
                "session_date": session_date
            })
            q_idx += 1
            curr_q = ""
            curr_ans = []
            in_ans = False

        for line in lines:
            s = clean_grammar_and_unescape(line)
            if not s:
                continue
            if s.startswith("#"):
                continue

            is_ans = s.startswith("* **Answer") or s.startswith("* **Suggestion") or s.startswith("* *Suggestion")
            is_sub_q = s.startswith("* *Sub-question:")

            if is_ans:
                in_ans = True
                curr_ans.append(s)
            elif is_sub_q:
                push_q()
                curr_q = s.replace("* *Sub-question:*", "").strip()
                in_ans = False
            elif s.endswith("?") or ("?" in s and not s.startswith("*")):
                push_q()
                curr_q = s
                in_ans = False
            elif in_ans:
                curr_ans.append(s)

        push_q()

        session_obj = {
            "session_id": "roopa_22_mar_2026",
            "session_name": session_date,
            "date": session_date,
            "timestamp": parse_date_ts(session_date),
            "questions": qs,
            "total_questions": len(qs)
        }

        return {
            "id": config["id"],
            "name": config["name"],
            "classes": config["classes"],
            "avatar_text": config["avatar_text"],
            "avatar_bg": config["avatar_bg"],
            "avatar_color": config["avatar_color"],
            "order": config["order"],
            "latest_date": session_date,
            "total_questions": len(qs),
            "sessions": [session_obj]
        }

    def _parse_krishna(self, config: Dict[str, Any], content: str) -> Dict[str, Any]:
        lines = content.splitlines()
        sessions = []
        curr_date = "11-Feb-2026"
        curr_qs = []
        curr_q = ""
        curr_ans = []
        in_ans = False
        curr_block_qs = []
        q_idx = 1

        def push_q():
            nonlocal curr_q, q_idx, curr_qs, curr_block_qs
            q_clean = clean_question_text(curr_q)
            if not q_clean:
                curr_q = ""
                return
            q_obj = {
                "id": f"qa_krishna_{q_idx}",
                "question": q_clean,
                "answer": "",
                "answer_html": "",
                "has_answer": False,
                "instructor": config["name"],
                "session_date": curr_date
            }
            q_idx += 1
            curr_qs.append(q_obj)
            curr_block_qs.append(q_obj)
            curr_q = ""

        def apply_block_ans():
            nonlocal curr_ans, in_ans, curr_block_qs
            ans_raw = "\n".join(curr_ans).strip()
            ans_clean = clean_grammar_and_unescape(ans_raw)
            has_ans = is_valid_answer_text(ans_clean)
            if has_ans:
                ans_html = render_md(ans_clean)
                for q_obj in curr_block_qs:
                    if not q_obj["has_answer"]:
                        q_obj["answer"] = ans_clean
                        q_obj["answer_html"] = ans_html
                        q_obj["has_answer"] = True
            curr_ans = []
            in_ans = False
            curr_block_qs = []

        def push_session():
            nonlocal curr_qs, curr_date, sessions
            push_q()
            apply_block_ans()
            if curr_qs:
                sessions.append({
                    "session_id": f"krishna_{curr_date.replace('-', '_')}",
                    "session_name": f"QA {curr_date}",
                    "date": curr_date,
                    "timestamp": parse_date_ts(curr_date),
                    "questions": list(curr_qs),
                    "total_questions": len(curr_qs)
                })
                curr_qs = []

        for line in lines:
            s = clean_grammar_and_unescape(line)
            if not s:
                if in_ans:
                    curr_ans.append("")
                continue

            if re.match(r'^#.*QA by Krishna', s, re.I):
                push_session()
                m_d = re.search(r'(\d{1,2}-[A-Za-z]+-\d{4})', s)
                if m_d:
                    curr_date = m_d.group(1).strip()
                continue

            if is_answer_start(s):
                push_q()
                in_ans = True
                curr_ans.append(s)
                continue

            if re.match(r'^(?:##\s*\*\*?\d+\.?|###\s*\*\*?\d+\.?|####\s*\*\*?\d+\.?|\*\*Part\s*\d+)', s, re.I):
                push_q()
                apply_block_ans()
                continue

            m_q = re.match(r'^(?:(?:\*|\d+\.)\s*(?:\*\*)?(?:Primary Question|Question|Sub-Question(?:\s*\d+)?):\*\*\s*|\*\s*(?:\*\*)?Question:\*\*\s*)(.*)', s, re.I)
            is_bullet_q = s.startswith('* ') and not is_answer_start(s) and ('?' in s or any(w in s for w in ['Explain', 'Describe', 'What', 'How', 'Why', 'Can you']))

            if m_q and len(m_q.group(1).strip()) > 3:
                if in_ans:
                    apply_block_ans()
                push_q()
                curr_q = m_q.group(1).strip()
            elif is_bullet_q:
                if in_ans:
                    apply_block_ans()
                push_q()
                curr_q = s[2:].strip()
            elif in_ans:
                curr_ans.append(s)

        push_session()
        sessions.sort(key=lambda s: s.get("timestamp", 0.0), reverse=True)
        total_q = sum(s["total_questions"] for s in sessions)
        latest_d = sessions[0]["date"] if sessions else "Recent"

        return {
            "id": config["id"],
            "name": config["name"],
            "classes": config["classes"],
            "avatar_text": config["avatar_text"],
            "avatar_bg": config["avatar_bg"],
            "avatar_color": config["avatar_color"],
            "order": config["order"],
            "latest_date": latest_d,
            "total_questions": total_q,
            "sessions": sessions
        }

    def _parse_topics(self, config: Dict[str, Any], content: str) -> Dict[str, Any]:
        lines = content.splitlines()
        sessions = []
        curr_topic = "Linux"
        curr_qs = []
        curr_q = ""
        curr_ans = []
        in_ans = False
        q_idx = 1

        def push_q():
            nonlocal curr_q, curr_ans, in_ans, q_idx
            q_clean = clean_question_text(curr_q)
            if not q_clean:
                curr_q = ""
                curr_ans = []
                in_ans = False
                return
            ans_clean = clean_grammar_and_unescape("\n".join(curr_ans)).strip()
            ans_clean = re.sub(r'^(?:Ans:|Answer:|\*Ans:\*)\s*', '', ans_clean, flags=re.I).strip()
            has_ans = is_valid_answer_text(ans_clean)
            curr_qs.append({
                "id": f"qa_topics_{q_idx}",
                "question": q_clean,
                "answer": ans_clean if has_ans else "",
                "answer_html": render_md(ans_clean) if has_ans else "",
                "has_answer": has_ans,
                "instructor": config["name"],
                "session_date": "Core Curriculum",
                "topic": curr_topic
            })
            q_idx += 1
            curr_q = ""
            curr_ans = []
            in_ans = False

        def push_topic():
            nonlocal curr_qs, curr_topic
            push_q()
            if curr_qs:
                sessions.append({
                    "session_id": f"topics_{curr_topic.lower().replace(' ', '_')}",
                    "session_name": curr_topic,
                    "date": "Core Curriculum",
                    "timestamp": 0.0,
                    "questions": list(curr_qs),
                    "total_questions": len(curr_qs)
                })
                curr_qs = []

        for line in lines:
            s = clean_grammar_and_unescape(line)
            if not s:
                if in_ans:
                    curr_ans.append("")
                continue

            if s.startswith("## "):
                push_topic()
                curr_topic = s[3:].replace('[', '').replace(']', '').replace(':', '').strip()
                continue

            m_q = re.match(r'^(\d+)[\.\)]\s*(.*)', s)
            m_ans = is_answer_start(s)

            if m_q and not m_ans:
                push_q()
                curr_q = m_q.group(2).strip()
                in_ans = False
            elif m_ans:
                in_ans = True
                curr_ans.append(s)
            elif in_ans:
                curr_ans.append(s)

        push_topic()
        total_q = sum(s["total_questions"] for s in sessions)

        return {
            "id": config["id"],
            "name": config["name"],
            "classes": config["classes"],
            "avatar_text": config["avatar_text"],
            "avatar_bg": config["avatar_bg"],
            "avatar_color": config["avatar_color"],
            "order": config["order"],
            "latest_date": "Core Reference",
            "total_questions": total_q,
            "sessions": sessions
        }

    def filter_qa(
        self,
        instructor: Optional[str] = "All",
        search: Optional[str] = "",
        sort_by: Optional[str] = "default",
        favorites: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        data = self.get_data()
        instructors = data.get("instructors", [])

        is_filter_inst = bool(instructor and instructor.strip().lower() not in ("all", ""))
        clean_inst = instructor.strip().lower() if is_filter_inst else ""
        s = search.strip().lower() if (search and search.strip()) else ""
        fav_set = set(favorites) if favorites else None

        filtered = []

        for inst in instructors:
            if is_filter_inst:
                if inst["id"].lower() != clean_inst and clean_inst not in inst["name"].lower():
                    continue

            inst_name = inst["name"].lower()
            matching_sessions = []

            for sess in inst.get("sessions", []):
                sess_name = sess.get("session_name", "").lower()
                sess_date = sess.get("date", "").lower()
                matching_qs = []

                for q in sess.get("questions", []):
                    q_id = q.get("id", "")
                    q_text = q.get("question", "").lower()
                    q_ans = q.get("answer", "").lower()
                    q_top = q.get("topic", "").lower()

                    if fav_set is not None and q_id not in fav_set:
                        continue

                    if s:
                        if not (s in inst_name or s in sess_name or s in sess_date or s in q_text or s in q_ans or s in q_top):
                            continue

                    matching_qs.append(q)

                if matching_qs:
                    s_copy = dict(sess)
                    s_copy["questions"] = matching_qs
                    s_copy["total_questions"] = len(matching_qs)
                    matching_sessions.append(s_copy)

            if matching_sessions:
                i_copy = dict(inst)
                i_copy["sessions"] = matching_sessions
                i_copy["total_questions"] = sum(s["total_questions"] for s in matching_sessions)
                filtered.append(i_copy)

        # Apply sorting
        if sort_by == "recent":
            filtered.sort(key=lambda x: (x.get("sessions", [{}])[0].get("timestamp", 0.0) if x.get("sessions") else 0.0), reverse=True)
        elif sort_by == "oldest":
            filtered.sort(key=lambda x: (x.get("sessions", [{}])[0].get("timestamp", 0.0) if x.get("sessions") else 0.0))
        elif sort_by == "most_questions":
            filtered.sort(key=lambda x: x.get("total_questions", 0), reverse=True)
        elif sort_by == "name_asc":
            filtered.sort(key=lambda x: x.get("name", "").lower())
        else:
            filtered.sort(key=lambda x: x.get("order", 99))

        return filtered

qa_service = QAService()
