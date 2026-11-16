import os
import re
import io
import html
import pickle
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from app.config import QA_SESSIONS_DIR

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
    if t.startswith('**') and t.endswith('**') and not (t.endswith(':**') or t.endswith(': **')):
        return False
    cleaned = re.sub(r'^[\*\-\#\s]+', '', t).strip()
    if re.match(r'^(?:Question|Candidate|Sub-Question|Primary Question|Main Question|Topic|\d+\.|\d+\))', cleaned, re.I):
        return False

    ans_keywords = [
        'instructor\'s general guidance', 'instructor general guidance', 'general instructor guidance',
        'instructor\'s guidance', 'instructor guidance', 'interviewer guidance',
        'instructor\'s suggestion / advice', 'instructor suggestion / advice',
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
        'instructor guidance & provided model answer',
        'feedback', 'instructor\'s feedback', 'instructor feedback',
        'feedback / guidance', 'feedback/guidance', 'feedback / advice', 'feedback/advice',
        'guidance / expected answer', 'guidance/expected answer', 'expected answer'
    ]
    cl = cleaned.lower().strip('*_ ')
    for kw in ans_keywords:
        if cl.startswith(kw):
            return True

    if re.search(r'instructor(?:[\'’]s)?\s+(?:general\s+)?(?:guidance|suggestion|advice|feedback|answer)', cleaned, re.I):
        return True

    if re.match(r'^(?:\*\*)?(?:Ans|Answer|Suggestion|Guidance|Feedback)(?:\*\*)?\s*:\s*', cleaned, re.I):
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
        "filename": "4.1. Hitish QA 59 to 88 class.md",
        "classes": "Class 59 to 88",
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
        "filename": "5. Aditya QA 69, 77, 89, 91-94 class.md",
        "classes": "Class 69, 77, 89, 91-94",
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
                # Try finding any file starting with same prefix in dir_path
                prefix = config["filename"].split("QA")[0].strip() if "QA" in config["filename"] else config["filename"][:5]
                matches = [f for f in os.listdir(self.dir_path) if f.startswith(prefix) and f.endswith(".md")]
                if matches:
                    fpath = os.path.join(self.dir_path, matches[0])
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

        # Order instructors by latest session timestamp (newest date first)
        instructors_data.sort(
            key=lambda x: (x.get("sessions", [{}])[0].get("timestamp", 0.0) if x.get("sessions") else 0.0),
            reverse=True
        )

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

        sess_seen_counts = {}
        def push_session():
            nonlocal curr_qs, curr_date, sessions
            push_q()
            apply_block_ans()
            if curr_qs:
                base_id = f"hitish_{curr_date.replace('-', '_')}"
                count = sess_seen_counts.get(base_id, 0) + 1
                sess_seen_counts[base_id] = count
                s_id = base_id if count == 1 else f"{base_id}_part{count}"
                sessions.append({
                    "session_id": s_id,
                    "session_name": curr_date if count == 1 else f"{curr_date} (Part {count})",
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
        curr_date = "General"
        curr_qs = []
        curr_q_obj = None
        curr_ans = []
        in_ans = False
        curr_topic = ""
        q_idx = 1

        def commit_ans():
            nonlocal curr_ans, in_ans, curr_q_obj, curr_qs, q_idx, curr_topic, curr_date
            if not in_ans and not curr_ans:
                return
            ans_raw = "\n".join(curr_ans).strip()
            ans_clean = clean_grammar_and_unescape(ans_raw)
            # Strictly strip any synthetic AI tags or labels if present
            ans_clean = re.sub(r'^(?:\*|_)?\s*(?:\*\*)?(?:Guidance\s*/\s*Expected\s*Answer|Verified\s*Production\s*Answer|Expected\s*Answer)(?:\*\*)?:?\s*', '', ans_clean, flags=re.I).strip()
            ans_clean = re.sub(r'^(?:[\*\-\s#_]*(?:\*\*)?Instructor(?:[\'’]s)?\s+[^\n]+(?:\*\*)?:?\s*\n+)', '', ans_clean, flags=re.I).strip()
            if is_valid_answer_text(ans_clean):
                if curr_q_obj is not None:
                    curr_q_obj["answer"] = ans_clean
                    curr_q_obj["answer_html"] = render_md(ans_clean)
                    curr_q_obj["has_answer"] = True
                    curr_q_obj = None
                else:
                    # Standalone instructor guidance block (e.g. at the start or end of a session)
                    title = curr_topic or "Instructor Guidance & Feedback"
                    q_item = {
                        "id": f"qa_aditya_{q_idx}",
                        "question": title,
                        "sub_questions": [],
                        "answer": ans_clean,
                        "answer_html": render_md(ans_clean),
                        "has_answer": True,
                        "instructor": config["name"],
                        "session_date": curr_date,
                        "topic": curr_topic or "Instructor Guidance",
                        "is_guidance_only": True
                    }
                    curr_qs.append(q_item)
                    q_idx += 1
            curr_ans = []
            in_ans = False

        def commit_q():
            nonlocal curr_q_obj
            commit_ans()
            curr_q_obj = None

        def push_session():
            nonlocal curr_qs, curr_date, sessions, curr_q_obj
            commit_q()
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
            raw_s = line.rstrip()
            s = clean_grammar_and_unescape(raw_s)
            if not s:
                if in_ans:
                    curr_ans.append("")
                continue

            # Session Header: ## 14-Nov-2026:
            m_d = re.match(r'^##\s*([0-9]{1,2}-[A-Za-z]+-[0-9]{4}):?', s)
            if m_d:
                push_session()
                curr_date = m_d.group(1).strip()
                curr_topic = ""
                continue

            # Check if this line starts an instructor suggestion / advice block
            if is_answer_start(s):
                commit_ans()
                in_ans = True
                curr_ans.append(s)
                continue

            # In answer accumulation mode: check if a new question or section starts
            if in_ans:
                is_new_section = False
                if s.startswith("**") and s.endswith("**") and len(s) > 4:
                    is_new_section = True
                elif re.match(r'^Candidate\s*\d+', s, re.I):
                    is_new_section = True
                elif s.startswith("* **Question") or s.startswith("- **Question") or s.startswith("Question:"):
                    is_new_section = True
                elif (s.startswith("* ") or s.startswith("- ")) and not re.match(r'^[\*\-\s]+(?:\*\*)?(?:Sub-question|Follow-up)', raw_s, re.I):
                    if s.startswith("* ") and not s.startswith("* -"):
                        if not re.search(r'^\*\s+\*\*On\s+[A-Za-z]', s):
                            is_new_section = True

                if is_new_section:
                    commit_q()
                else:
                    curr_ans.append(s)
                    continue

            # Topic Header: **Topic Name**
            if s.startswith("**") and s.endswith("**") and len(s) > 4:
                topic_title = s.strip('*').strip()
                if "Candidate" not in topic_title and "Questions Asked" not in topic_title:
                    commit_q()
                    curr_topic = topic_title
                continue

            # Candidate Header
            if re.match(r'^Candidate\s*\d+', s, re.I):
                commit_q()
                continue

            # Sub-question detection
            m_sub = re.match(r'^[\*\-\s]+(?:\*\*)?(?:Sub-question|Follow-up)(?:\:|\*+\:)?\s*(.*)', raw_s, re.I)
            if m_sub:
                sub_text = clean_question_text(m_sub.group(1))
                if sub_text and curr_q_obj is not None:
                    curr_q_obj["sub_questions"].append(sub_text)
                continue

            # Main Question detection
            if s.startswith("* ") or s.startswith("- ") or s.startswith("Question:"):
                # If indented under an active question, treat as sub-question
                if (raw_s.startswith("  ") or raw_s.startswith("\t")) and curr_q_obj is not None:
                    clean_sub = clean_question_text(s.lstrip("*- \t"))
                    if clean_sub:
                        curr_q_obj["sub_questions"].append(clean_sub)
                        continue

                commit_q()
                q_text = clean_question_text(s)
                if q_text:
                    curr_q_obj = {
                        "id": f"qa_aditya_{q_idx}",
                        "question": q_text,
                        "sub_questions": [],
                        "answer": "",
                        "answer_html": "",
                        "has_answer": False,
                        "instructor": config["name"],
                        "session_date": curr_date,
                        "topic": curr_topic
                    }
                    curr_qs.append(curr_q_obj)
                    q_idx += 1
                continue

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
        sort_by: Optional[str] = "recent",
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
        if sort_by == "oldest":
            filtered.sort(key=lambda x: (x.get("sessions", [{}])[0].get("timestamp", 0.0) if x.get("sessions") else 0.0))
        elif sort_by == "most_questions":
            filtered.sort(key=lambda x: x.get("total_questions", 0), reverse=True)
        elif sort_by == "name_asc":
            filtered.sort(key=lambda x: x.get("name", "").lower())
        elif sort_by == "instructor_order":
            filtered.sort(key=lambda x: x.get("order", 99))
        else:
            # Default to "recent" / newest session date first
            filtered.sort(key=lambda x: (x.get("sessions", [{}])[0].get("timestamp", 0.0) if x.get("sessions") else 0.0), reverse=True)

        return filtered

    def get_session(self, session_id: str, instructor_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Find a session by its session_id across all instructors (or within an instructor)."""
        data = self.get_data()
        for inst in data.get("instructors", []):
            if instructor_id and inst.get("id") != instructor_id:
                continue
            for sess in inst.get("sessions", []):
                if sess.get("session_id") == session_id:
                    res = dict(sess)
                    res["instructor_id"] = inst.get("id")
                    res["instructor_name"] = inst.get("name")
                    res["instructor_classes"] = inst.get("classes")
                    return res
        return None

    def get_instructor(self, instructor_id: str) -> Optional[Dict[str, Any]]:
        """Find an instructor by instructor_id."""
        data = self.get_data()
        for inst in data.get("instructors", []):
            if inst.get("id") == instructor_id:
                return inst
        return None

    def generate_session_markdown(self, sess: Dict[str, Any]) -> str:
        """Format a session and all its questions into a clean, complete Markdown document."""
        inst_name = sess.get("instructor_name", "ArtisanTek Faculty")
        inst_classes = sess.get("instructor_classes", "")
        sess_name = sess.get("session_name", "QA Session")
        sess_date = sess.get("date", "")
        questions = sess.get("questions", [])
        total_q = len(questions)
        answered_q = sum(1 for q in questions if q.get("has_answer"))

        lines = [
            f"# DevOps QA Session: {sess_name}",
            "",
            f"- **Instructor:** {inst_name}{f' ({inst_classes})' if inst_classes else ''}",
        ]
        if sess_date and sess_date != sess_name:
            lines.append(f"- **Date:** {sess_date}")
        else:
            lines.append(f"- **Date / Topic:** {sess_date or sess_name}")

        lines.extend([
            f"- **Total Questions:** {total_q} ({answered_q} with Instructor Guidance)",
            "- **Source:** DevOps Knowledge Portal & Interview Hub",
            "",
            "---",
            ""
        ])

        # Group consecutive questions with identical non-empty answer to avoid repetitive text
        grouped = []
        q_counter = 1
        for q in questions:
            ans = q.get("answer", "").strip()
            if grouped and grouped[-1]["answer"] and grouped[-1]["answer"] == ans:
                grouped[-1]["questions"].append((q_counter, q))
            else:
                grouped.append({
                    "questions": [(q_counter, q)],
                    "answer": ans,
                    "topic": q.get("topic"),
                })
            q_counter += 1

        for g in grouped:
            qs = g["questions"]
            topic = g["topic"]
            ans_text = g["answer"]
            has_ans = bool(ans_text)

            if len(qs) == 1:
                num, q = qs[0]
                q_text = q.get("question", "").strip()
                lines.append(f"### Q{num}. {q_text}")
                if topic:
                    lines.append(f"*Topic: {topic}*")
                lines.append("")
            else:
                first_num = qs[0][0]
                last_num = qs[-1][0]
                heading_topic = f" - {topic}" if topic else ""
                lines.append(f"### Q{first_num} – Q{last_num}{heading_topic}")
                for num, q in qs:
                    lines.append(f"- **Q{num}.** {q.get('question', '').strip()}")
                lines.append("")

            if has_ans and ans_text:
                lines.append(ans_text)
            else:
                lines.append("*Question only (No answer recorded in session transcript).*")

            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def generate_instructor_markdown(self, inst: Dict[str, Any]) -> str:
        """Format all sessions for an instructor into a comprehensive Markdown document."""
        inst_name = inst.get("name", "ArtisanTek Faculty")
        inst_classes = inst.get("classes", "")
        sessions = inst.get("sessions", [])
        total_q = inst.get("total_questions", 0)
        answered_q = sum(
            sum(1 for q in s.get("questions", []) if q.get("has_answer"))
            for s in sessions
        )

        lines = [
            f"# DevOps QA Sessions: {inst_name}",
            "",
            f"- **Instructor:** {inst_name}{f' ({inst_classes})' if inst_classes else ''}",
            f"- **Total Sessions:** {len(sessions)}",
            f"- **Total Questions:** {total_q} ({answered_q} with Instructor Guidance)",
            "- **Source:** DevOps Knowledge Portal & Interview Hub",
            "",
            "---",
            ""
        ]

        for s_idx, sess in enumerate(sessions, 1):
            sess_name = sess.get("session_name", "QA Session")
            sess_date = sess.get("date", "")
            questions = sess.get("questions", [])
            s_answered = sum(1 for q in questions if q.get("has_answer"))

            lines.append(f"## Session {s_idx}: {sess_name}")
            if sess_date and sess_date != sess_name:
                lines.append(f"**Date:** {sess_date} | **Questions:** {len(questions)} ({s_answered} with guidance)")
            else:
                lines.append(f"**Date / Topic:** {sess_date or sess_name} | **Questions:** {len(questions)} ({s_answered} with guidance)")
            lines.append("")

            grouped = []
            q_counter = 1
            for q in questions:
                ans = q.get("answer", "").strip()
                if grouped and grouped[-1]["answer"] and grouped[-1]["answer"] == ans:
                    grouped[-1]["questions"].append((q_counter, q))
                else:
                    grouped.append({
                        "questions": [(q_counter, q)],
                        "answer": ans,
                        "topic": q.get("topic"),
                    })
                q_counter += 1

            for g in grouped:
                qs = g["questions"]
                topic = g["topic"]
                ans_text = g["answer"]
                has_ans = bool(ans_text)

                if len(qs) == 1:
                    num, q = qs[0]
                    q_text = q.get("question", "").strip()
                    lines.append(f"### Q{num}. {q_text}")
                    if topic:
                        lines.append(f"*Topic: {topic}*")
                    lines.append("")
                else:
                    first_num = qs[0][0]
                    last_num = qs[-1][0]
                    heading_topic = f" - {topic}" if topic else ""
                    lines.append(f"### Q{first_num} – Q{last_num}{heading_topic}")
                    for num, q in qs:
                        lines.append(f"- **Q{num}.** {q.get('question', '').strip()}")
                    lines.append("")

                if has_ans and ans_text:
                    lines.append(ans_text)
                else:
                    lines.append("*Question only (No answer recorded in session transcript).*")

                lines.append("")
                lines.append("---")
                lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _clean_pdf_text(text: str) -> str:
        """Replace Unicode symbols and special characters that ReportLab/xhtml2pdf fonts cannot render."""
        if not text:
            return ""
        replacements = {
            "↳": "- ",
            "●": "&bull;",
            "🏢": "",
            "📁": "",
            "├──": "|-- ",
            "└──": "\\-- ",
            "│": "|",
            "├": "|-",
            "└": "\\-",
            "─": "-",
            "—": "--",
            "–": "-",
            "’": "'",
            "‘": "'",
            "“": '"',
            "”": '"',
            "•": "&bull;",
            "…": "...",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def generate_session_html(self, sess: Dict[str, Any]) -> str:
        """Format a session and all its questions into clean, minimalist HTML for PDF rendering."""
        inst_name = sess.get("instructor_name", "ArtisanTek Faculty")
        inst_classes = sess.get("instructor_classes", "")
        sess_name = sess.get("session_name", "QA Session")
        sess_date = sess.get("date", "")
        questions = sess.get("questions", [])
        total_q = len(questions)

        q_items_html = []
        for idx, q in enumerate(questions, 1):
            q_text = html.escape(self._clean_pdf_text(q.get("question", "").strip()))
            topic = q.get("topic", "").strip()
            sub_questions = q.get("sub_questions", [])
            has_ans = bool(q.get("has_answer"))
            ans = (q.get("answer") or "").strip()
            # Strictly strip any residual synthetic AI tags if present
            ans = re.sub(r'^(?:\*|_)?\s*(?:\*\*)?(?:Guidance\s*/\s*Expected\s*Answer|Verified\s*Production\s*Answer|Expected\s*Answer)(?:\*\*)?:?\s*', '', ans, flags=re.I).strip()
            ans = re.sub(r'^(?:[\*\-\s#_]*(?:\*\*)?Instructor(?:[\'’]s)?\s+[^\n]+(?:\*\*)?:?\s*\n+)', '', ans, flags=re.I).strip()
            ans_html = q.get("answer_html", "") or render_md(ans)
            ans_html = self._clean_pdf_text(ans_html)

            # Sub-questions HTML
            sub_html = ""
            if sub_questions:
                sub_lis = "".join([
                    f'<li>{html.escape(self._clean_pdf_text(sub))}</li>'
                    for sub in sub_questions
                ])
                sub_html = f'''
                <div class="subquestions-wrap">
                    <div class="subquestions-header">Follow-up / Sub-questions:</div>
                    <ul class="subquestions-list">{sub_lis}</ul>
                </div>
                '''

            # Guidance HTML (Only instructor suggestions / guidance, never synthetic AI answers)
            guidance_html = ""
            if has_ans and ans_html.strip():
                guidance_html = f'''
                <div class="guidance-box">
                    <div class="guidance-header"><strong>Instructor\'s Suggestion &amp; Guidance:</strong></div>
                    <div class="guidance-body">{ans_html}</div>
                </div>
                '''

            topic_badge = f' <span class="item-topic">({html.escape(topic)})</span>' if topic else ""

            q_items_html.append(f'''
            <div class="question-item">
                <div class="question-title">Q{idx}. {q_text}{topic_badge}</div>
                {sub_html}
                {guidance_html}
            </div>
            ''')

        css = """
        @page {
            size: A4 portrait;
            margin: 1.0cm 1.0cm 1.0cm 1.0cm;
            @bottom-right {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 7.5pt;
                color: #777777;
                font-family: Helvetica, Arial, sans-serif;
            }
            @bottom-left {
                content: "DevOps Interview Hub • ArtisanTek QA Sessions";
                font-size: 7.5pt;
                color: #999999;
                font-family: Helvetica, Arial, sans-serif;
            }
        }
        body {
            font-family: Helvetica, Arial, sans-serif;
            font-size: 8.5pt;
            line-height: 1.35;
            color: #111111;
        }
        .doc-header {
            border-bottom: 1.5px solid #333333;
            padding-bottom: 4px;
            margin-bottom: 10px;
        }
        .doc-title {
            font-size: 13pt;
            font-weight: bold;
            color: #111111;
            margin: 0 0 2px 0;
        }
        .doc-meta {
            font-size: 8pt;
            color: #555555;
            margin: 0;
        }
        .question-item {
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 1px solid #e5e7eb;
            page-break-inside: auto;
        }
        .question-title {
            font-size: 9pt;
            font-weight: bold;
            color: #111111;
            margin-bottom: 4px;
            page-break-after: avoid;
        }
        .item-topic {
            font-size: 7.8pt;
            font-weight: normal;
            color: #4b5563;
        }
        .subquestions-wrap {
            margin: 3px 0 5px 10px;
        }
        .subquestions-header {
            font-size: 7.8pt;
            font-weight: bold;
            color: #374151;
            margin-bottom: 2px;
        }
        .subquestions-list {
            margin: 0 0 0 14px;
            padding: 0;
            font-size: 8.2pt;
            color: #1f2937;
        }
        .subquestions-list li {
            margin-bottom: 2px;
            line-height: 1.3;
        }
        .guidance-box {
            background-color: #f8fafc;
            border-left: 2.5px solid #2563eb;
            padding: 4px 8px;
            margin: 4px 0 2px 8px;
            font-size: 8.2pt;
            line-height: 1.35;
        }
        .guidance-header {
            font-size: 8pt;
            color: #1e40af;
            margin-bottom: 2px;
        }
        .guidance-body {
            color: #1f2937;
        }
        p {
            margin: 2px 0 3px 0;
        }
        pre, code {
            font-family: Courier, monospace;
            font-size: 7.2pt;
            background-color: #f6f6f6;
            color: #111111;
        }
        pre {
            padding: 4px 6px;
            border: 1px solid #e0e0e0;
            margin: 3px 0;
        }
        ul, ol {
            margin: 2px 0 3px 14px;
            padding: 0;
        }
        li {
            margin-bottom: 1.5px;
        }
        """

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>QA Session: {html.escape(sess_name)}</title>
<style>{css}</style>
</head>
<body>
    <div class="doc-header">
        <div class="doc-title">DevOps QA Session: {html.escape(sess_name)}</div>
        <div class="doc-meta">
            <strong>Instructor:</strong> {html.escape(inst_name)}{f' ({html.escape(inst_classes)})' if inst_classes else ''} &bull; 
            <strong>Date:</strong> {html.escape(sess_date or sess_name)} &bull; 
            <strong>Total Questions:</strong> {total_q}
        </div>
    </div>
    {''.join(q_items_html)}
</body>
</html>"""

    def generate_session_pdf(self, sess: Dict[str, Any]) -> bytes:
        """Convert a session HTML into a PDF byte stream."""
        html_str = self.generate_session_html(sess)
        buf = io.BytesIO()
        if pisa:
            pisa.CreatePDF(html_str, dest=buf)
        return buf.getvalue()

    def generate_instructor_html(self, inst: Dict[str, Any]) -> str:
        """Format an instructor's full set of sessions into clean, minimalist HTML for PDF rendering."""
        inst_name = inst.get("name", "ArtisanTek Faculty")
        inst_classes = inst.get("classes", "")
        sessions = inst.get("sessions", [])
        total_q = inst.get("total_questions", 0)

        session_sections = []
        for s_idx, sess in enumerate(sessions, 1):
            sess_name = sess.get("session_name", "QA Session")
            sess_date = sess.get("date", "")
            questions = sess.get("questions", [])

            q_items_html = []
            for idx, q in enumerate(questions, 1):
                q_text = html.escape(self._clean_pdf_text(q.get("question", "").strip()))
                topic = q.get("topic", "").strip()
                sub_questions = q.get("sub_questions", [])
                has_ans = bool(q.get("has_answer"))
                ans = (q.get("answer") or "").strip()
                ans = re.sub(r'^(?:\*|_)?\s*(?:\*\*)?(?:Guidance\s*/\s*Expected\s*Answer|Verified\s*Production\s*Answer|Expected\s*Answer)(?:\*\*)?:?\s*', '', ans, flags=re.I).strip()
                ans = re.sub(r'^(?:[\*\-\s#_]*(?:\*\*)?Instructor(?:[\'’]s)?\s+[^\n]+(?:\*\*)?:?\s*\n+)', '', ans, flags=re.I).strip()
                ans_html = q.get("answer_html", "") or render_md(ans)
                ans_html = self._clean_pdf_text(ans_html)

                sub_html = ""
                if sub_questions:
                    sub_lis = "".join([
                        f'<li>{html.escape(self._clean_pdf_text(sub))}</li>'
                        for sub in sub_questions
                    ])
                    sub_html = f'''
                    <div class="subquestions-wrap">
                        <div class="subquestions-header">Follow-up / Sub-questions:</div>
                        <ul class="subquestions-list">{sub_lis}</ul>
                    </div>
                    '''

                guidance_html = ""
                if has_ans and ans_html.strip():
                    guidance_html = f'''
                    <div class="guidance-box">
                        <div class="guidance-header"><strong>Instructor\'s Suggestion &amp; Guidance:</strong></div>
                        <div class="guidance-body">{ans_html}</div>
                    </div>
                    '''

                topic_badge = f' <span class="item-topic">({html.escape(topic)})</span>' if topic else ""

                q_items_html.append(f'''
                <div class="question-item">
                    <div class="question-title">Q{idx}. {q_text}{topic_badge}</div>
                    {sub_html}
                    {guidance_html}
                </div>
                ''')

            session_sections.append(f'''
            <div class="session-section">
                <div class="section-title">Session {s_idx}: {html.escape(sess_name)} ({html.escape(sess_date or sess_name)}) &bull; {len(questions)} Questions</div>
                {''.join(q_items_html)}
            </div>
            ''')

        css = """
        @page {
            size: A4 portrait;
            margin: 1.0cm 1.0cm 1.0cm 1.0cm;
            @bottom-right {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 7.5pt;
                color: #777777;
                font-family: Helvetica, Arial, sans-serif;
            }
            @bottom-left {
                content: "DevOps Interview Hub • ArtisanTek Faculty QA";
                font-size: 7.5pt;
                color: #999999;
                font-family: Helvetica, Arial, sans-serif;
            }
        }
        body {
            font-family: Helvetica, Arial, sans-serif;
            font-size: 8.5pt;
            line-height: 1.35;
            color: #111111;
        }
        .doc-header {
            border-bottom: 1.5px solid #333333;
            padding-bottom: 4px;
            margin-bottom: 10px;
        }
        .doc-title {
            font-size: 13pt;
            font-weight: bold;
            color: #111111;
            margin: 0 0 2px 0;
        }
        .doc-meta {
            font-size: 8pt;
            color: #555555;
            margin: 0;
        }
        .section-title {
            font-size: 10pt;
            font-weight: bold;
            color: #111111;
            border-bottom: 1px solid #dddddd;
            padding-bottom: 2px;
            margin: 12px 0 6px 0;
            page-break-after: avoid;
        }
        .question-item {
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 1px solid #e5e7eb;
            page-break-inside: auto;
        }
        .question-title {
            font-size: 9pt;
            font-weight: bold;
            color: #111111;
            margin-bottom: 4px;
            page-break-after: avoid;
        }
        .item-topic {
            font-size: 7.8pt;
            font-weight: normal;
            color: #4b5563;
        }
        .subquestions-wrap {
            margin: 3px 0 5px 10px;
        }
        .subquestions-header {
            font-size: 7.8pt;
            font-weight: bold;
            color: #374151;
            margin-bottom: 2px;
        }
        .subquestions-list {
            margin: 0 0 0 14px;
            padding: 0;
            font-size: 8.2pt;
            color: #1f2937;
        }
        .subquestions-list li {
            margin-bottom: 2px;
            line-height: 1.3;
        }
        .guidance-box {
            background-color: #f8fafc;
            border-left: 2.5px solid #2563eb;
            padding: 4px 8px;
            margin: 4px 0 2px 8px;
            font-size: 8.2pt;
            line-height: 1.35;
        }
        .guidance-header {
            font-size: 8pt;
            color: #1e40af;
            margin-bottom: 2px;
        }
        .guidance-body {
            color: #1f2937;
        }
        p {
            margin: 2px 0 3px 0;
        }
        pre, code {
            font-family: Courier, monospace;
            font-size: 7.2pt;
            background-color: #f6f6f6;
            color: #111111;
        }
        pre {
            padding: 4px 6px;
            border: 1px solid #e0e0e0;
            margin: 3px 0;
        }
        ul, ol {
            margin: 2px 0 3px 14px;
            padding: 0;
        }
        li {
            margin-bottom: 1.5px;
        }
        """

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>QA Sessions: {html.escape(inst_name)}</title>
<style>{css}</style>
</head>
<body>
    <div class="doc-header">
        <div class="doc-title">DevOps QA Collection: {html.escape(inst_name)}</div>
        <div class="doc-meta">
            <strong>Instructor:</strong> {html.escape(inst_name)}{f' ({html.escape(inst_classes)})' if inst_classes else ''} &bull; 
            <strong>Total Sessions:</strong> {len(sessions)} &bull; 
            <strong>Total Questions:</strong> {total_q}
        </div>
    </div>
    {''.join(session_sections)}
</body>
</html>"""

    def generate_instructor_pdf(self, inst: Dict[str, Any]) -> bytes:
        """Convert instructor HTML into a PDF byte stream."""
        html_str = self.generate_instructor_html(inst)
        buf = io.BytesIO()
        if pisa:
            pisa.CreatePDF(html_str, dest=buf)
        return buf.getvalue()

qa_service = QAService()
