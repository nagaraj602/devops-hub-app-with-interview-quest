import os
import re
import json
import uuid
import base64
import mimetypes
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import io

from app.config import INTERVIEW_SCHEDULES_DIR, ATTACHMENTS_DIR
from app.services.company_logo_service import get_company_logo_meta

def format_indian_date(val: Optional[str]) -> str:
    """Formats any date string into Indian standard date format: DD-Mon-YYYY (e.g. 24-Nov-2026)."""
    if not val:
        return ""
    val = str(val).strip()
    if re.match(r'^\d{2}-[A-Za-z]{3}-\d{4}$', val):
        return val
    for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%b-%Y", "%d %b %Y", "%B %d, %Y"]:
        try:
            dt = datetime.strptime(val, fmt)
            return dt.strftime("%d-%b-%Y")
        except ValueError:
            pass
    if "T" in val:
        try:
            dt = datetime.fromisoformat(val)
            return dt.strftime("%d-%b-%Y")
        except Exception:
            pass
    return val

class InterviewScheduleService:
    def __init__(self):
        self.base_dir = Path(INTERVIEW_SCHEDULES_DIR)
        self.attachments_dir = Path(ATTACHMENTS_DIR)
        self.schedules_file = self.base_dir / "schedules.json"
        self.companies_file = self.base_dir / "companies.json"
        self.rounds_file = self.base_dir / "rounds.json"

        # Ensure directories exist
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.attachments_dir.mkdir(parents=True, exist_ok=True)

        self._schedules_cache: Optional[List[Dict[str, Any]]] = None
        self._companies_cache: Optional[List[Dict[str, Any]]] = None
        self._rounds_cache: Optional[List[str]] = None

        # Initialize data files if not present or empty
        self._initialize_data()

    def _default_rounds(self) -> List[str]:
        return [
            "HR Round",
            "Technical Round 1",
            "Technical Round 2",
            "Level 1",
            "Level 2",
            "Face to face round",
            "System Design Round",
            "Managerial / Cultural Fit Round"
        ]

    def _initialize_data(self):
        # 1. Rounds
        if not self.rounds_file.exists():
            rounds = self._default_rounds()
            self._save_rounds(rounds)
        else:
            try:
                with open(self.rounds_file, "r", encoding="utf-8") as f:
                    self._rounds_cache = json.load(f)
            except Exception:
                self._rounds_cache = self._default_rounds()
                self._save_rounds(self._rounds_cache)

        # 2. Companies
        if not self.companies_file.exists():
            self._companies_cache = []
            self._save_companies([])
        else:
            try:
                with open(self.companies_file, "r", encoding="utf-8") as f:
                    self._companies_cache = json.load(f)
            except Exception:
                self._companies_cache = []
                self._save_companies([])

        # 3. Schedules
        if not self.schedules_file.exists() or os.path.getsize(self.schedules_file) <= 2:
            self._schedules_cache = []
            self._auto_import_from_question_bank()
        else:
            try:
                with open(self.schedules_file, "r", encoding="utf-8") as f:
                    self._schedules_cache = json.load(f)
            except Exception:
                self._schedules_cache = []
                self._auto_import_from_question_bank()

    def _trigger_git_commit(self, msg: str):
        try:
            from app.services.git_storage_service import git_storage_service
            git_storage_service.commit_and_push_async(["content/interview_schedules/", "logs/"], msg)
        except Exception as e:
            print(f"Notice: git commit failed to trigger: {e}")

    def _save_schedules(self, schedules: List[Dict[str, Any]], trigger_git: bool = True):
        self._schedules_cache = schedules
        with open(self.schedules_file, "w", encoding="utf-8") as f:
            json.dump(schedules, f, indent=2, ensure_ascii=False)
        if trigger_git:
            self._trigger_git_commit(f"chore(schedule): update interview schedules data [{datetime.now().strftime('%d-%b-%Y %H:%M')}]")

    def _save_companies(self, companies: List[Dict[str, Any]], trigger_git: bool = True):
        self._companies_cache = companies
        with open(self.companies_file, "w", encoding="utf-8") as f:
            json.dump(companies, f, indent=2, ensure_ascii=False)
        if trigger_git:
            self._trigger_git_commit(f"chore(schedule): update companies list [{datetime.now().strftime('%d-%b-%Y %H:%M')}]")

    def _save_rounds(self, rounds: List[str], trigger_git: bool = True):
        # Deduplicate while preserving order
        unique_rounds = []
        for r in rounds:
            cleaned = r.strip()
            if cleaned and cleaned not in unique_rounds:
                unique_rounds.append(cleaned)
        self._rounds_cache = unique_rounds
        with open(self.rounds_file, "w", encoding="utf-8") as f:
            json.dump(unique_rounds, f, indent=2, ensure_ascii=False)
        if trigger_git:
            self._trigger_git_commit(f"chore(schedule): update round types [{datetime.now().strftime('%d-%b-%Y %H:%M')}]")

    def _parse_qb_datetime(self, date_str: str) -> tuple[str, str, str]:
        """Parses QB date string like '23-Nov-2026 03:00 PM' into (YYYY-MM-DD, HH:MM AM/PM, HH:MM AM/PM)."""
        if not date_str:
            now = datetime.now()
            return now.strftime("%Y-%m-%d"), "10:00 AM", "11:00 AM"

        cleaned = date_str.replace("*", "").strip()
        try:
            dt = datetime.strptime(cleaned, "%d-%b-%Y %I:%M %p")
            end_dt = dt + timedelta(hours=1)
            return dt.strftime("%Y-%m-%d"), dt.strftime("%I:%M %p"), end_dt.strftime("%I:%M %p")
        except Exception:
            pass

        try:
            dt = datetime.strptime(cleaned, "%d-%m-%Y %H:%M")
            end_dt = dt + timedelta(hours=1)
            return dt.strftime("%Y-%m-%d"), dt.strftime("%I:%M %p"), end_dt.strftime("%I:%M %p")
        except Exception:
            pass

        try:
            dt = datetime.strptime(cleaned.split()[0], "%d-%m-%Y")
            return dt.strftime("%Y-%m-%d"), "10:00 AM", "11:00 AM"
        except Exception:
            pass

        return datetime.now().strftime("%Y-%m-%d"), "10:00 AM", "11:00 AM"

    def _auto_import_from_question_bank(self):
        """Imports existing Nagaraj interviews from Question Bank service into schedules."""
        try:
            from app.services.question_bank_service import question_bank_service
            data = question_bank_service.get_data()
        except Exception as e:
            print(f"Notice: question_bank_service not ready for import: {e}")
            return

        imported_schedules = []
        companies_map = {c["name"].lower(): c for c in (self._companies_cache or [])}
        rounds_set = set(self._rounds_cache or self._default_rounds())

        nagaraj_companies = [c for c in data.get("companies", []) if c.get("is_nagaraj_interview")]

        for comp in nagaraj_companies:
            comp_name = comp.get("company_name", "").strip()
            if not comp_name:
                continue

            # Ensure company exists in companies cache
            if comp_name.lower() not in companies_map:
                logo_meta = get_company_logo_meta(comp_name)
                comp_obj = {
                    "id": re.sub(r'[^a-zA-Z0-9]', '_', comp_name).lower(),
                    "name": comp_name,
                    "logo_url": logo_meta.get("logo_url", ""),
                    "initials": logo_meta.get("initials", comp_name[:2].upper()),
                    "avatar_bg": logo_meta.get("avatar_bg", "#ffffff"),
                    "avatar_color": logo_meta.get("avatar_color", "#2563eb"),
                    "created_at": datetime.now().isoformat()
                }
                companies_map[comp_name.lower()] = comp_obj

            for rnd in comp.get("rounds", []):
                rnd_name = rnd.get("round_name", "Level 1").strip()
                rnd_date_raw = rnd.get("date", "")
                parsed_date, start_t, end_t = self._parse_qb_datetime(rnd_date_raw)
                rnd_id = rnd.get("round_id", "")
                q_count = len(rnd.get("questions", []))

                rounds_set.add(rnd_name)

                sched_id = f"sched_imp_{re.sub(r'[^a-zA-Z0-9]', '_', comp_name).lower()}_{re.sub(r'[^a-zA-Z0-9]', '_', rnd_name).lower()}_{parsed_date}"

                # Default experience based on questions
                initial_exp = f"Attended {rnd_name} for {comp_name}. Discussed {q_count} core DevOps architecture and troubleshooting questions recorded in Question Bank."

                imported_schedules.append({
                    "id": sched_id,
                    "company_name": comp_name,
                    "round_name": rnd_name,
                    "date": parsed_date,
                    "start_time": start_t,
                    "end_time": end_t,
                    "hr_email": "",
                    "hr_phone": "",
                    "status": "Completed",
                    "cancellation_reason": "",
                    "emails": [
                        {
                            "id": f"em_{uuid.uuid4().hex[:8]}",
                            "subject": f"Interview Confirmation - {comp_name} ({rnd_name})",
                            "body": f"Interview invitation for Nagaraj - {comp_name} - {rnd_name} on {parsed_date} at {start_t}.\n\nMode: Video Conference / Technical Assessment.",
                            "date": parsed_date
                        }
                    ],
                    "screenshots": [],
                    "experience": initial_exp,
                    "transcript": "",
                    "has_transcript": False,
                    "round_id": rnd_id,
                    "youtube_url": "",
                    "question_count": q_count,
                    "qb_link": f"/question-bank?search={comp_name}#{rnd_id}" if rnd_id else f"/question-bank?search={comp_name}",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                })

        # Group imported schedules by company to assign round order and sequential links
        schedules_by_comp: Dict[str, List[Dict[str, Any]]] = {}
        for s in imported_schedules:
            schedules_by_comp.setdefault(s["company_name"], []).append(s)

        final_imported = []
        for c_name, c_scheds in schedules_by_comp.items():
            # Sort chronologically (earliest to latest) for round progression
            c_scheds.sort(key=lambda x: (x.get("date", ""), x.get("start_time", "")))
            for idx, s in enumerate(c_scheds):
                s["round_order"] = idx + 1
                if idx < len(c_scheds) - 1:
                    s["next_round_id"] = c_scheds[idx + 1]["id"]
                else:
                    s["next_round_id"] = ""
                final_imported.append(s)

        # Save companies, rounds, and imported schedules
        self._save_companies(list(companies_map.values()))
        self._save_rounds(list(rounds_set))
        self._save_schedules(final_imported)

    def resolve_qb_match(self, company_name: str, round_name: str, qb_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Resolves matching round in Question Bank for a given company and round name."""
        if not company_name:
            return {"round_id": "", "question_count": 0, "qb_link": "/question-bank"}

        if qb_data is None:
            try:
                from app.services.question_bank_service import question_bank_service
                qb_data = question_bank_service.get_data()
            except Exception:
                qb_data = {}

        def norm(s: str) -> str:
            return re.sub(r'[^a-zA-Z0-9]', '', (s or '')).lower()

        c_norm = norm(company_name)
        r_norm = norm(round_name)

        matched_round_id = ""
        matched_q_count = 0
        company_found = False

        for comp in qb_data.get("companies", []):
            comp_name_qb = comp.get("company_name", "")
            comp_qb_norm = norm(comp_name_qb)
            if comp_qb_norm == c_norm or (c_norm and (c_norm in comp_qb_norm or comp_qb_norm in c_norm)):
                company_found = True
                for rnd in comp.get("rounds", []):
                    rnd_qb_name = rnd.get("round_name", "")
                    rnd_qb_norm = norm(rnd_qb_name)
                    if rnd_qb_norm == r_norm or (r_norm and (r_norm in rnd_qb_norm or rnd_qb_norm in r_norm)):
                        matched_round_id = rnd.get("round_id", "")
                        matched_q_count = len(rnd.get("questions", []))
                        break
                if matched_round_id:
                    break

        encoded_company = re.sub(r'\s+', '+', company_name.strip())
        if matched_round_id:
            qb_link = f"/question-bank?search={encoded_company}#{matched_round_id}"
        else:
            qb_link = f"/question-bank?search={encoded_company}"

        return {
            "round_id": matched_round_id,
            "question_count": matched_q_count,
            "qb_link": qb_link
        }

    def sync_with_question_bank(self, qb_data: Optional[Dict[str, Any]] = None) -> int:
        """Syncs all existing schedules with Question Bank data to update question counts and deep links."""
        schedules = list(self.get_all_schedules())
        updated_count = 0
        for s in schedules:
            res = self.resolve_qb_match(s.get("company_name", ""), s.get("round_name", ""), qb_data)
            changed = False
            if res.get("round_id") and s.get("round_id") != res["round_id"]:
                s["round_id"] = res["round_id"]
                changed = True
            if res.get("question_count") != s.get("question_count"):
                s["question_count"] = res["question_count"]
                changed = True
            if res.get("qb_link") and s.get("qb_link") != res["qb_link"]:
                s["qb_link"] = res["qb_link"]
                changed = True
            if changed:
                s["updated_at"] = datetime.now().isoformat()
                updated_count += 1

        if updated_count > 0:
            self._save_schedules(schedules)
        return updated_count

    def get_companies(self) -> List[Dict[str, Any]]:
        if self._companies_cache is None:
            self._initialize_data()
        return self._companies_cache or []

    def get_rounds(self) -> List[str]:
        if self._rounds_cache is None:
            self._initialize_data()
        return self._rounds_cache or self._default_rounds()

    def get_all_schedules(self) -> List[Dict[str, Any]]:
        if self._schedules_cache is None:
            self._initialize_data()
        for s in (self._schedules_cache or []):
            s["indian_date"] = format_indian_date(s.get("date", ""))
            s["display_date"] = s["indian_date"]
            if not s.get("round_id") or s.get("question_count", 0) == 0:
                match = self.resolve_qb_match(s.get("company_name", ""), s.get("round_name", ""))
                if match.get("round_id"):
                    s["round_id"] = match["round_id"]
                    s["question_count"] = match["question_count"]
                    s["qb_link"] = match["qb_link"]
        # Sort descending by date, then start_time
        def sort_key(s):
            d = s.get("date", "1970-01-01")
            t = s.get("start_time", "00:00")
            return (d, t)
        return sorted(self._schedules_cache or [], key=sort_key, reverse=True)

    def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        schedules = self.get_all_schedules()
        for s in schedules:
            if s.get("id") == schedule_id:
                return s
        return None

    def save_schedule(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates or updates an interview schedule item."""
        schedules = list(self.get_all_schedules())
        schedule_id = data.get("id") or f"sched_{uuid.uuid4().hex[:10]}"
        now_iso = datetime.now().isoformat()

        company_name = data.get("company_name", "").strip()
        round_name = data.get("round_name", "").strip()

        # Update companies cache if company is new
        if company_name:
            comps = self.get_companies()
            existing_comp_names = [c["name"].lower() for c in comps]
            if company_name.lower() not in existing_comp_names:
                logo_meta = get_company_logo_meta(company_name)
                comp_obj = {
                    "id": re.sub(r'[^a-zA-Z0-9]', '_', company_name).lower(),
                    "name": company_name,
                    "logo_url": logo_meta.get("logo_url", ""),
                    "initials": logo_meta.get("initials", company_name[:2].upper()),
                    "avatar_bg": logo_meta.get("avatar_bg", "#ffffff"),
                    "avatar_color": logo_meta.get("avatar_color", "#2563eb"),
                    "created_at": now_iso
                }
                comps.append(comp_obj)
                self._save_companies(comps)

        # Update rounds cache if round is new
        if round_name:
            rounds = self.get_rounds()
            if round_name not in rounds:
                rounds.append(round_name)
                self._save_rounds(rounds)

        # Format emails
        raw_emails = data.get("emails", [])
        formatted_emails = []
        if isinstance(raw_emails, list):
            for em in raw_emails:
                if isinstance(em, dict) and (em.get("subject") or em.get("body")):
                    formatted_emails.append({
                        "id": em.get("id") or f"em_{uuid.uuid4().hex[:8]}",
                        "subject": em.get("subject", "").strip(),
                        "body": em.get("body", "").strip(),
                        "date": em.get("date") or data.get("date", "")
                    })

        # Screenshots
        raw_screenshots = data.get("screenshots", [])
        formatted_screenshots = []
        if isinstance(raw_screenshots, list):
            for sc in raw_screenshots:
                if isinstance(sc, dict) and sc.get("filename"):
                    formatted_screenshots.append({
                        "id": sc.get("id") or f"sc_{uuid.uuid4().hex[:8]}",
                        "filename": sc.get("filename"),
                        "original_name": sc.get("original_name") or sc.get("filename"),
                        "url": sc.get("url") or f"/api/admin/interview-schedules/attachment/{sc.get('filename')}"
                    })

        # Resolve Question Bank link and question count if not explicitly set
        qb_match = self.resolve_qb_match(company_name, round_name)
        round_id = data.get("round_id") or qb_match.get("round_id", "")
        question_count = int(data.get("question_count") or 0)
        if question_count == 0 and qb_match.get("question_count", 0) > 0:
            question_count = qb_match.get("question_count", 0)
        qb_link = data.get("qb_link")
        if not qb_link or qb_link == f"/question-bank?search={company_name}":
            qb_link = qb_match.get("qb_link", f"/question-bank?search={company_name}")

        # Prepare schedule record
        sched_record = {
            "id": schedule_id,
            "company_name": company_name,
            "round_name": round_name,
            "date": data.get("date", "").strip(),
            "start_time": data.get("start_time", "").strip(),
            "end_time": data.get("end_time", "").strip(),
            "hr_email": data.get("hr_email", "").strip(),
            "hr_phone": data.get("hr_phone", "").strip(),
            "youtube_url": str(data.get("youtube_url") or "").strip(),
            "status": data.get("status", "Scheduled"),
            "cancellation_reason": data.get("cancellation_reason", "").strip(),
            "emails": formatted_emails,
            "screenshots": formatted_screenshots,
            "experience": data.get("experience", "").strip(),
            "transcript": data.get("transcript", "").strip(),
            "has_transcript": bool(data.get("has_transcript", False)),
            "round_id": round_id,
            "round_order": int(data.get("round_order") or 1),
            "next_round_id": data.get("next_round_id", "").strip(),
            "question_count": question_count,
            "qb_link": qb_link,
            "updated_at": now_iso
        }

        # Check if updating existing
        existing_idx = next((i for i, s in enumerate(schedules) if s.get("id") == schedule_id), None)
        if existing_idx is not None:
            sched_record["created_at"] = schedules[existing_idx].get("created_at", now_iso)
            schedules[existing_idx] = sched_record
        else:
            sched_record["created_at"] = now_iso
            schedules.insert(0, sched_record)

        self._save_schedules(schedules)
        return sched_record

    def update_status(self, schedule_id: str, status: str, cancellation_reason: str = "", has_transcript: Optional[bool] = None, transcript: Optional[str] = None, youtube_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
        schedules = list(self.get_all_schedules())
        for s in schedules:
            if s.get("id") == schedule_id:
                s["status"] = status
                if cancellation_reason is not None:
                    s["cancellation_reason"] = cancellation_reason
                if has_transcript is not None:
                    s["has_transcript"] = has_transcript
                if transcript is not None:
                    s["transcript"] = transcript
                if youtube_url is not None:
                    s["youtube_url"] = youtube_url.strip()
                s["updated_at"] = datetime.now().isoformat()
                self._save_schedules(schedules)
                return s
        return None

    def update_youtube_url(self, schedule_id: str, youtube_url: str) -> Optional[Dict[str, Any]]:
        schedules = list(self.get_all_schedules())
        for s in schedules:
            if s.get("id") == schedule_id:
                s["youtube_url"] = (youtube_url or "").strip()
                s["updated_at"] = datetime.now().isoformat()
                self._save_schedules(schedules)
                return s
        return None

    def delete_schedule(self, schedule_id: str) -> bool:
        schedules = list(self.get_all_schedules())
        filtered = [s for s in schedules if s.get("id") != schedule_id]
        if len(filtered) != len(schedules):
            self._save_schedules(filtered)
            return True
        return False

    def save_attachment(self, file_bytes: bytes, original_filename: str) -> Dict[str, Any]:
        """Saves screenshot attachment losslessly with original bytes."""
        ext = Path(original_filename).suffix.lower()
        if not ext:
            ext = ".png"
        clean_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', Path(original_filename).stem)
        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}_{clean_name}{ext}"
        target_path = self.attachments_dir / unique_filename

        with open(target_path, "wb") as f:
            f.write(file_bytes)

        self._trigger_git_commit(f"chore(attachment): upload interview screenshot {unique_filename}")

        return {
            "id": f"sc_{uuid.uuid4().hex[:8]}",
            "filename": unique_filename,
            "original_name": original_filename,
            "url": f"/api/admin/interview-schedules/attachment/{unique_filename}",
            "size": len(file_bytes)
        }

    def get_attachment_path(self, filename: str) -> Optional[Path]:
        safe_name = os.path.basename(filename)
        file_path = self.attachments_dir / safe_name
        if file_path.exists() and file_path.is_file():
            return file_path
        return None

    def get_weekly_data(self, target_date_str: Optional[str] = None) -> Dict[str, Any]:
        """Calculates week-by-week calendar graph stats."""
        if target_date_str:
            try:
                target_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
            except Exception:
                target_dt = datetime.now()
        else:
            target_dt = datetime.now()

        # Find Monday of target week
        monday = target_dt - timedelta(days=target_dt.weekday())
        sunday = monday + timedelta(days=6)

        week_dates = [(monday + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        schedules = self.get_all_schedules()
        schedules_by_date: Dict[str, List[Dict[str, Any]]] = {}
        for s in schedules:
            d = s.get("date", "")
            if d:
                schedules_by_date.setdefault(d, []).append(s)

        days_data = []
        total_week_count = 0
        scheduled_count = 0
        completed_count = 0
        cancelled_count = 0
        rescheduled_count = 0

        for i, d_str in enumerate(week_dates):
            d_schedules = schedules_by_date.get(d_str, [])
            count = len(d_schedules)
            total_week_count += count
            for s in d_schedules:
                st = s.get("status", "Scheduled")
                if st == "Completed":
                    completed_count += 1
                elif st == "Cancelled":
                    cancelled_count += 1
                elif st == "Rescheduled":
                    rescheduled_count += 1
                else:
                    scheduled_count += 1

            dt_obj = datetime.strptime(d_str, "%Y-%m-%d")
            days_data.append({
                "date": d_str,
                "formatted_date": format_indian_date(d_str),
                "indian_date": format_indian_date(d_str),
                "day_name": day_names[i],
                "count": count,
                "schedules": d_schedules
            })

        prev_week = (monday - timedelta(days=7)).strftime("%Y-%m-%d")
        next_week = (monday + timedelta(days=7)).strftime("%Y-%m-%d")

        return {
            "week_start": monday.strftime("%Y-%m-%d"),
            "week_end": sunday.strftime("%Y-%m-%d"),
            "formatted_week_label": f"{format_indian_date(monday.strftime('%Y-%m-%d'))} – {format_indian_date(sunday.strftime('%Y-%m-%d'))}",
            "days": days_data,
            "total_count": total_week_count,
            "scheduled_count": scheduled_count,
            "completed_count": completed_count,
            "cancelled_count": cancelled_count,
            "rescheduled_count": rescheduled_count,
            "prev_week": prev_week,
            "next_week": next_week
        }

    def get_monthly_data(self, target_month_str: Optional[str] = None) -> Dict[str, Any]:
        """Calculates month-by-month calendar activity stats."""
        import calendar
        if target_month_str:
            try:
                parts = target_month_str.split("-")
                year, month = int(parts[0]), int(parts[1])
            except Exception:
                now = datetime.now()
                year, month = now.year, now.month
        else:
            now = datetime.now()
            year, month = now.year, now.month

        # Days in month & weekday of 1st day (0 = Monday, 6 = Sunday)
        first_weekday, num_days = calendar.monthrange(year, month)
        first_date = datetime(year, month, 1)
        month_label = first_date.strftime("%B %Y")
        current_month_str = f"{year:04d}-{month:02d}"

        # Previous and Next month strings
        if month == 1:
            prev_month_str = f"{year - 1:04d}-12"
        else:
            prev_month_str = f"{year:04d}-{month - 1:02d}"

        if month == 12:
            next_month_str = f"{year + 1:04d}-01"
        else:
            next_month_str = f"{year:04d}-{month + 1:02d}"

        schedules = self.get_all_schedules()
        schedules_by_date: Dict[str, List[Dict[str, Any]]] = {}
        for s in schedules:
            d = s.get("date", "")
            if d:
                schedules_by_date.setdefault(d, []).append(s)

        days_data = []
        total_month_count = 0
        scheduled_count = 0
        completed_count = 0
        cancelled_count = 0
        rescheduled_count = 0

        day_names_short = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        for day_num in range(1, num_days + 1):
            dt_obj = datetime(year, month, day_num)
            d_str = dt_obj.strftime("%Y-%m-%d")
            d_schedules = schedules_by_date.get(d_str, [])
            count = len(d_schedules)
            total_month_count += count

            for s in d_schedules:
                st = s.get("status", "Scheduled")
                if st == "Completed":
                    completed_count += 1
                elif st == "Cancelled":
                    cancelled_count += 1
                elif st == "Rescheduled":
                    rescheduled_count += 1
                else:
                    scheduled_count += 1

            days_data.append({
                "day_number": day_num,
                "date": d_str,
                "formatted_date": format_indian_date(d_str),
                "indian_date": format_indian_date(d_str),
                "day_name": day_names_short[dt_obj.weekday()],
                "weekday": dt_obj.weekday(),
                "count": count,
                "schedules": d_schedules
            })

        return {
            "month_str": current_month_str,
            "formatted_month_label": month_label,
            "first_weekday": first_weekday,  # 0 = Monday ... 6 = Sunday
            "total_days": num_days,
            "days": days_data,
            "total_count": total_month_count,
            "scheduled_count": scheduled_count,
            "completed_count": completed_count,
            "cancelled_count": cancelled_count,
            "rescheduled_count": rescheduled_count,
            "prev_month": prev_month_str,
            "next_month": next_month_str
        }

    def reorder_rounds(self, company_name: str, ordered_ids: List[str]) -> List[Dict[str, Any]]:
        """Updates the sequential order and arrow connections between rounds for a company."""
        schedules = list(self.get_all_schedules())
        id_to_order = {sid: idx + 1 for idx, sid in enumerate(ordered_ids)}
        id_to_next = {}
        for idx in range(len(ordered_ids) - 1):
            id_to_next[ordered_ids[idx]] = ordered_ids[idx + 1]

        updated_items = []
        for s in schedules:
            if s.get("company_name", "").strip().lower() == company_name.strip().lower() and s["id"] in id_to_order:
                s["round_order"] = id_to_order[s["id"]]
                s["next_round_id"] = id_to_next.get(s["id"], "")
                updated_items.append(s)

        self._save_schedules(schedules)
        return updated_items

    def generate_pdf_report(self) -> bytes:
        """Generates professional PDF document using xhtml2pdf."""
        from xhtml2pdf import pisa
        html_content = self._render_report_html(for_pdf=True)
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
        if pisa_status.err:
            raise RuntimeError(f"PDF generation error code {pisa_status.err}")
        return pdf_buffer.getvalue()

    def generate_editable_report(self, format_type: str = "doc") -> str:
        """Generates editable document (Word-compatible HTML .doc or Markdown .md)."""
        if format_type.lower() == "md":
            return self._render_report_markdown()
        # Returns rich Word-compatible HTML document
        return self._render_report_html(for_pdf=False)

    def _get_image_base64_data_uri(self, filename: str) -> str:
        """Reads local attachment image losslessly and formats as data URI for standalone reports."""
        img_path = self.get_attachment_path(filename)
        if not img_path:
            return ""
        mime_type, _ = mimetypes.guess_type(str(img_path))
        if not mime_type:
            mime_type = "image/png"
        try:
            with open(img_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
                return f"data:{mime_type};base64,{encoded}"
        except Exception:
            return ""

    def _render_report_markdown(self) -> str:
        """Generates universal editable Markdown (.md) report."""
        schedules = self.get_all_schedules()
        total = len(schedules)
        completed = sum(1 for s in schedules if s.get("status") == "Completed")
        cancelled = sum(1 for s in schedules if s.get("status") == "Cancelled")
        scheduled = sum(1 for s in schedules if s.get("status") == "Scheduled")

        lines = [
            "# Nagaraj's Comprehensive Interview Schedules & Activity Report",
            f"*Generated on: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}*",
            "",
            "## 1. Executive Summary",
            f"- **Total Interviews Recorded:** {total}",
            f"- **Completed:** {completed}",
            f"- **Scheduled / Upcoming:** {scheduled}",
            f"- **Cancelled / Postponed:** {cancelled}",
            "",
            "---",
            "",
            "## 2. Interview Schedule Dossier",
            ""
        ]

        for idx, s in enumerate(schedules, 1):
            comp = s.get("company_name", "N/A")
            rnd = s.get("round_name", "N/A")
            date_val = format_indian_date(s.get("date", "N/A"))
            start_t = s.get("start_time", "")
            end_t = s.get("end_time", "")
            status = s.get("status", "Scheduled")
            hr_mail = s.get("hr_email", "N/A")
            hr_ph = s.get("hr_phone", "N/A")

            lines.append(f"### {idx}. {comp} — {rnd}")
            lines.append(f"- **Date & Time:** {date_val} ({start_t} - {end_t})")
            lines.append(f"- **Status:** `{status}`")
            lines.append(f"- **HR Contact:** Email: {hr_mail} | Phone: {hr_ph}")
            if s.get("youtube_url"):
                lines.append(f"- **YouTube Recording:** [{s.get('youtube_url')}]({s.get('youtube_url')})")
            if s.get("cancellation_reason"):
                lines.append(f"- **Cancellation Reason:** {s.get('cancellation_reason')}")

            # Emails
            emails = s.get("emails", [])
            if emails:
                lines.append("")
                lines.append("#### Received Communications / Emails:")
                for em_i, em in enumerate(emails, 1):
                    subj = em.get("subject", "No Subject")
                    body = em.get("body", "").replace("\n", "\n> ")
                    lines.append(f"**Email {em_i}: {subj}**")
                    lines.append(f"> {body}")
                    lines.append("")

            # Screenshots
            screenshots = s.get("screenshots", [])
            if screenshots:
                lines.append("")
                lines.append("#### Screenshot Attachments:")
                for sc in screenshots:
                    lines.append(f"- Attached screenshot: `{sc.get('original_name')}` ({sc.get('filename')})")

            # Experience
            exp = s.get("experience", "").strip()
            if exp:
                lines.append("")
                lines.append("#### Candidate Interview Experience & Reflection:")
                lines.append(exp)

            # Transcript
            has_t = s.get("has_transcript", False)
            t_text = s.get("transcript", "").strip()
            lines.append("")
            lines.append("#### Interview Transcript:")
            if has_t and t_text:
                lines.append(t_text)
            else:
                lines.append("*No transcript recorded / toggled as not available.*")

            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _render_report_html(self, for_pdf: bool = False) -> str:
        """Renders styled professional HTML report for PDF export or Word .doc."""
        schedules = self.get_all_schedules()
        total = len(schedules)
        completed = sum(1 for s in schedules if s.get("status") == "Completed")
        cancelled = sum(1 for s in schedules if s.get("status") == "Cancelled")
        scheduled = sum(1 for s in schedules if s.get("status") == "Scheduled")

        items_html = []
        for idx, s in enumerate(schedules, 1):
            comp = s.get("company_name", "N/A")
            rnd = s.get("round_name", "N/A")
            date_val = format_indian_date(s.get("date", "N/A"))
            start_t = s.get("start_time", "")
            end_t = s.get("end_time", "")
            status = s.get("status", "Scheduled")
            hr_mail = s.get("hr_email") or "Not provided"
            hr_ph = s.get("hr_phone") or "Not provided"
            exp = s.get("experience", "").strip()
            transcript = s.get("transcript", "").strip()
            has_transcript = s.get("has_transcript", False)

            # Status pill style
            status_color = "#16a34a" if status == "Completed" else ("#dc2626" if status == "Cancelled" else "#2563eb")

            # Emails HTML
            emails_html = ""
            for em_i, em in enumerate(s.get("emails", []), 1):
                subj = em.get("subject", "No Subject")
                body = em.get("body", "").replace("\n", "<br>")
                emails_html += f"""
                <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:10px 14px; margin-bottom:8px;">
                    <div style="font-weight:bold; color:#1e293b; font-size:13px; margin-bottom:4px;">Email #{em_i}: {subj}</div>
                    <div style="color:#334155; font-size:12px; line-height:1.5;">{body}</div>
                </div>
                """
            if not emails_html:
                emails_html = "<div style='color:#94a3b8; font-size:12px; font-style:italic;'>No email body recorded.</div>"

            # Screenshots HTML
            screens_html = ""
            for sc in s.get("screenshots", []):
                fname = sc.get("filename", "")
                img_src = self._get_image_base64_data_uri(fname)

                if img_src:
                    screens_html += f"""
                    <div style="margin-top:10px; margin-bottom:12px;">
                        <div style="font-size:11px; color:#64748b; margin-bottom:4px;">Attached: <strong>{sc.get('original_name', fname)}</strong></div>
                        <img src="{img_src}" style="max-width:100%; border:1px solid #cbd5e1; border-radius:6px;" alt="Email Screenshot" />
                    </div>
                    """
                else:
                    screens_html += f"<div style='font-size:12px; color:#64748b;'>Attached: {sc.get('original_name', fname)} (File: {fname})</div>"

            # Transcript block
            transcript_html = ""
            if has_transcript and transcript:
                formatted_transcript = transcript.replace("\n", "<br>")
                transcript_html = f"<div style='background:#f1f5f9; padding:10px 14px; border-radius:6px; font-size:11px; line-height:1.4; color:#1e293b;'>{formatted_transcript}</div>"
            else:
                transcript_html = "<div style='color:#94a3b8; font-size:12px; font-style:italic;'>No transcript available / Not recorded</div>"

            page_break = "page-break-before:always;" if idx > 1 else ""
            items_html.append(f"""
            <div style="border:1px solid #cbd5e1; border-radius:8px; padding:16px; margin-bottom:24px; {page_break}">
                <div style="border-bottom:2px solid #0284c7; padding-bottom:8px; margin-bottom:12px;">
                    <table style="width:100%; border-collapse:collapse;">
                        <tr>
                            <td style="font-size:18px; font-weight:bold; color:#0f172a;">{idx}. {comp} &mdash; {rnd}</td>
                            <td style="text-align:right;">
                                <span style="background:{status_color}; color:#ffffff; padding:4px 10px; border-radius:12px; font-size:11px; font-weight:bold; text-transform:uppercase;">{status}</span>
                            </td>
                        </tr>
                    </table>
                </div>

                <table style="width:100%; border-collapse:collapse; margin-bottom:12px; font-size:12px;">
                    <tr>
                        <td style="width:50%; padding:4px 0; color:#475569;"><strong>Date & Time:</strong> {date_val} ({start_t} &ndash; {end_t})</td>
                        <td style="width:50%; padding:4px 0; color:#475569;"><strong>HR Email:</strong> {hr_mail}</td>
                    </tr>
                    <tr>
                        <td style="padding:4px 0; color:#475569;"><strong>HR Phone:</strong> {hr_ph}</td>
                        <td style="padding:4px 0; color:#475569;"><strong>Questions Count:</strong> {s.get('question_count', 0)} questions documented</td>
                    </tr>
                    {f"<tr><td colspan='2' style='padding:4px 0; color:#dc2626;'><strong>YouTube Recording:</strong> <a href='{s.get('youtube_url')}' style='color:#dc2626;'>{s.get('youtube_url')}</a></td></tr>" if s.get('youtube_url') else ""}
                    {f"<tr><td colspan='2' style='padding:4px 0; color:#dc2626;'><strong>Cancellation Note:</strong> {s.get('cancellation_reason')}</td></tr>" if s.get('cancellation_reason') else ""}
                </table>

                <div style="margin-top:10px;">
                    <h4 style="margin:0 0 6px 0; font-size:13px; color:#0f172a; text-transform:uppercase; letter-spacing:0.5px;">Email Communications</h4>
                    {emails_html}
                </div>

                {f'''
                <div style="margin-top:14px;">
                    <h4 style="margin:0 0 6px 0; font-size:13px; color:#0f172a; text-transform:uppercase; letter-spacing:0.5px;">Screenshot Proof & Email Capture</h4>
                    {screens_html}
                </div>
                ''' if screens_html else ''}

                <div style="margin-top:14px;">
                    <h4 style="margin:0 0 6px 0; font-size:13px; color:#0f172a; text-transform:uppercase; letter-spacing:0.5px;">Candidate Experience & Reflections</h4>
                    <div style="background:#f8fafc; border-left:4px solid #0284c7; padding:10px 14px; font-size:12px; color:#334155; line-height:1.5;">
                        {exp.replace(chr(10), '<br>') if exp else '<span style=\"color:#94a3b8; font-style:italic;\">No experience summary recorded.</span>'}
                    </div>
                </div>

                <div style="margin-top:14px;">
                    <h4 style="margin:0 0 6px 0; font-size:13px; color:#0f172a; text-transform:uppercase; letter-spacing:0.5px;">Interview Transcript</h4>
                    {transcript_html}
                </div>
            </div>
            """)

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Nagaraj Interview Schedules & Activity Report</title>
<style>
    @page {{
        size: a4 portrait;
        margin: 1.5cm;
        @bottom-right {{
            content: "Page " counter(page) " of " counter(pages);
            font-size: 9px;
            color: #94a3b8;
        }}
    }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        color: #1e293b;
        line-height: 1.4;
        margin: 0;
        padding: 0;
    }}
    .header {{
        border-bottom: 3px solid #0284c7;
        padding-bottom: 12px;
        margin-bottom: 20px;
    }}
    .title {{
        font-size: 24px;
        font-weight: bold;
        color: #0f172a;
        margin: 0 0 4px 0;
    }}
    .subtitle {{
        font-size: 13px;
        color: #64748b;
        margin: 0;
    }}
    .summary-card {{
        background: #f1f5f9;
        border-radius: 8px;
        padding: 12px 18px;
        margin-bottom: 24px;
    }}
    .summary-table {{
        width: 100%;
        border-collapse: collapse;
        text-align: center;
    }}
    .summary-val {{
        font-size: 20px;
        font-weight: bold;
        color: #0284c7;
    }}
    .summary-lbl {{
        font-size: 11px;
        color: #64748b;
        text-transform: uppercase;
        font-weight: bold;
    }}
</style>
</head>
<body>
    <div class="header">
        <h1 class="title">Nagaraj &mdash; DevOps Interview Activity & Schedules Dossier</h1>
        <p class="subtitle">Official Comprehensive Report &bull; Generated on {datetime.now().strftime('%d-%b-%Y %I:%M %p')}</p>
    </div>

    <div class="summary-card">
        <table class="summary-table">
            <tr>
                <td style="width:25%;">
                    <div class="summary-val">{total}</div>
                    <div class="summary-lbl">Total Interviews</div>
                </td>
                <td style="width:25%;">
                    <div class="summary-val" style="color:#16a34a;">{completed}</div>
                    <div class="summary-lbl">Completed</div>
                </td>
                <td style="width:25%;">
                    <div class="summary-val" style="color:#2563eb;">{scheduled}</div>
                    <div class="summary-lbl">Scheduled / Active</div>
                </td>
                <td style="width:25%;">
                    <div class="summary-val" style="color:#dc2626;">{cancelled}</div>
                    <div class="summary-lbl">Cancelled / Postponed</div>
                </td>
            </tr>
        </table>
    </div>

    <div>
        {''.join(items_html)}
    </div>
</body>
</html>"""
        return html

# Singleton instance
interview_schedule_service = InterviewScheduleService()
