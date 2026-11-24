import hmac
import hashlib
import binascii
from fastapi import APIRouter, Request, Response, Form, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from app.config import ADMIN_PORT, PORT, ADMIN_PASSWORD, ADMIN_PASSWORD_HASH, ADMIN_PASSWORD_SALT
from app.services.page_visibility_service import page_visibility_service
from app.services.interview_schedule_service import interview_schedule_service

router = APIRouter()

COOKIE_NAME = "devops_hub_admin_auth"

def verify_admin_password(password: str) -> bool:
    if not password:
        return False
    # Check PBKDF2 hash (100,000 iterations with salt)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), ADMIN_PASSWORD_SALT, 100000)
    computed_hex = binascii.hexlify(key).decode('utf-8')
    if hmac.compare_digest(computed_hex, ADMIN_PASSWORD_HASH):
        return True
    if ADMIN_PASSWORD and hmac.compare_digest(password, ADMIN_PASSWORD):
        return True
    return False

def _get_expected_auth_token() -> str:
    return hashlib.sha256((ADMIN_PASSWORD_HASH + "_devops_admin_session").encode()).hexdigest()

def is_admin_server_request(request: Request) -> bool:
    """
    Checks whether the request is hitting the dedicated admin port (ADMIN_PORT=9256)
    or dedicated admin hostname (e.g. admin.sidorea.shop).
    """
    # 1. Check ASGI server listening port
    server = request.scope.get("server")
    if server and len(server) >= 2 and server[1] == ADMIN_PORT:
        return True

    # 2. Check Host header (hostname or explicit port)
    host_header = (request.headers.get("host") or "").lower()
    host_without_port = host_header.split(":")[0]
    if host_without_port.startswith("admin."):
        return True
    if ":" in host_header:
        try:
            port = int(host_header.split(":")[1])
            if port == ADMIN_PORT:
                return True
        except ValueError:
            pass

    # 3. Check request.url.port
    try:
        if request.url.port == ADMIN_PORT:
            return True
    except Exception:
        pass

    # 4. Check Forwarded / Proxy headers
    xf_port = request.headers.get("x-forwarded-port")
    if xf_port:
        try:
            if int(xf_port) == ADMIN_PORT:
                return True
        except ValueError:
            pass
    xf_host = (request.headers.get("x-forwarded-host") or "").lower()
    if xf_host.split(":")[0].startswith("admin."):
        return True

    return False

def is_admin_request(request: Request) -> bool:
    """
    Determines whether a request comes from an authenticated admin on the dedicated admin domain/port.
    Admin access is strictly forbidden and unavailable on the public portal (port 8926).
    Authentication requires a valid session token cookie or token header/query.
    """
    # Admin privileges can only be exercised on the dedicated admin port / admin domain
    if not is_admin_server_request(request):
        return False

    # 1. Check HTTP cookie
    cookie_val = request.cookies.get(COOKIE_NAME)
    if cookie_val and hmac.compare_digest(cookie_val, _get_expected_auth_token()):
        return True

    # 2. Check query parameter token or header
    param_token = request.query_params.get("token") or request.headers.get("X-Admin-Token")
    if param_token and (verify_admin_password(param_token) or hmac.compare_digest(param_token, _get_expected_auth_token())):
        return True

    return False

class VisibilityTogglePayload(BaseModel):
    page_key: str
    is_published: bool

async def admin_portal_view(request: Request):
    """
    Renders the Admin Dashboard directly.
    Called when visiting '/' on port 9256 (or admin.sidorea.shop).
    """
    if not is_admin_server_request(request):
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "page_title": "Page Not Found",
                "active_page": "404"
            },
            status_code=404
        )

    v_map = page_visibility_service.get_visibility_map()
    pages_list = list(v_map.values())
    
    published_count = sum(1 for p in pages_list if p.get("is_published", True))
    hidden_count = sum(1 for p in pages_list if not p.get("is_published", True))
    
    is_auth = is_admin_request(request)
    
    # Load Interview Schedules & Activity Data
    schedules_list = interview_schedule_service.get_all_schedules()
    companies_list = interview_schedule_service.get_companies()
    rounds_list = interview_schedule_service.get_rounds()
    weekly_data = interview_schedule_service.get_weekly_data()

    total_schedules = len(schedules_list)
    completed_schedules = sum(1 for s in schedules_list if s.get("status") == "Completed")
    scheduled_count = sum(1 for s in schedules_list if s.get("status") == "Scheduled")
    cancelled_schedules = sum(1 for s in schedules_list if s.get("status") == "Cancelled")
    rescheduled_count = sum(1 for s in schedules_list if s.get("status") == "Rescheduled")

    # Group schedules by company for company boxes
    schedules_by_company: Dict[str, List[Dict[str, Any]]] = {}
    for s in schedules_list:
        c_name = s.get("company_name", "").strip()
        schedules_by_company.setdefault(c_name, []).append(s)

    companies_with_boxes = []
    for c in companies_list:
        c_name = c.get("name", "")
        c_scheds = schedules_by_company.get(c_name, [])
        if not c_scheds and c_name.lower() == "google":
            continue

        # Sort rounds inside company sequentially (Round 1 -> Round 2 -> Round 3 ...)
        sorted_rounds = sorted(c_scheds, key=lambda s: (s.get("round_order", 1), s.get("date", "")))

        # Find latest schedule for activity sorting
        latest_s = max(c_scheds, key=lambda s: (s.get("date", ""), s.get("start_time", "")), default=None) if c_scheds else None

        companies_with_boxes.append({
            "meta": c,
            "schedules": sorted_rounds,
            "total_rounds": len(c_scheds),
            "completed_rounds": sum(1 for s in c_scheds if s.get("status") == "Completed"),
            "latest_schedule": latest_s
        })

    # Sort company rows by most recent interview activity descending (most recent first)
    def comp_sort_key(cb):
        ls = cb.get("latest_schedule")
        if ls:
            return (ls.get("date", ""), ls.get("start_time", ""))
        return ("", "")
    companies_with_boxes.sort(key=comp_sort_key, reverse=True)

    monthly_data = interview_schedule_service.get_monthly_data()
    active_tab = request.query_params.get("tab", "interviews")

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "page_title": "Admin Portal — Interview Activity & Publisher",
            "active_page": "admin",
            "active_tab": active_tab,
            "is_admin": is_auth,
            "is_authenticated": is_auth,
            "pages": pages_list,
            "total_pages": len(pages_list),
            "published_count": published_count,
            "hidden_count": hidden_count,
            "admin_port": ADMIN_PORT,
            "main_port": PORT,
            "host_header": request.headers.get("host", ""),
            "schedules": schedules_list,
            "companies": companies_list,
            "company_boxes": companies_with_boxes,
            "rounds": rounds_list,
            "weekly_data": weekly_data,
            "monthly_data": monthly_data,
            "total_schedules": total_schedules,
            "completed_schedules": completed_schedules,
            "scheduled_count": scheduled_count,
            "cancelled_schedules": cancelled_schedules,
            "rescheduled_count": rescheduled_count
        }
    )

@router.get("/admin", response_class=HTMLResponse)
async def admin_url_handler(request: Request):
    """
    Handler for explicit /admin path:
    - On dedicated admin port (9256): do NOT add /admin to URL -> redirect to '/'
    - On public port (8926): /admin path does NOT work -> return 404
    """
    if is_admin_server_request(request):
        redirect_url = "/"
        if request.url.query:
            redirect_url += f"?{request.url.query}"
        return RedirectResponse(url=redirect_url, status_code=307)

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="404.html",
        context={
            "page_title": "Page Not Found",
            "active_page": "404"
        },
        status_code=404
    )

@router.post("/api/admin/login")
async def admin_login(request: Request, response: Response):
    if not is_admin_server_request(request):
        raise HTTPException(status_code=404, detail="Not Found")

    try:
        data = await request.json()
        password = data.get("password", "")
    except Exception:
        password = ""

    if verify_admin_password(password):
        token = _get_expected_auth_token()
        res = JSONResponse({"status": "success", "message": "Authentication successful. Controls unlocked."})
        res.set_cookie(
            key=COOKIE_NAME,
            value=token,
            max_age=86400 * 30,  # 30 days
            httponly=True,
            samesite="lax",
            path="/"
        )
        return res
    else:
        return JSONResponse({"status": "error", "message": "Invalid administrator passphrase."}, status_code=401)

@router.get("/admin/logout")
@router.get("/logout")
@router.post("/api/admin/logout")
async def admin_logout(request: Request, response: Response):
    if not is_admin_server_request(request):
        raise HTTPException(status_code=404, detail="Not Found")

    if request.method == "GET":
        res = RedirectResponse(url="/", status_code=303)
    else:
        res = JSONResponse({"status": "success", "message": "Logged out successfully."})

    res.delete_cookie(key=COOKIE_NAME, path="/")
    res.delete_cookie(key=COOKIE_NAME)
    return res

@router.post("/api/admin/toggle-visibility")
async def toggle_visibility(payload: VisibilityTogglePayload, request: Request):
    if not is_admin_server_request(request):
        raise HTTPException(status_code=404, detail="Not Found")

    if not is_admin_request(request):
        return JSONResponse({"status": "error", "message": "Unauthorized. Please enter administrator passphrase to modify settings."}, status_code=403)

    result = page_visibility_service.set_page_visibility(
        page_key=payload.page_key,
        is_published=payload.is_published,
        updated_by="Admin Portal (Web UI)"
    )

    v_map = page_visibility_service.get_visibility_map()
    pages_list = list(v_map.values())
    result["published_count"] = sum(1 for p in pages_list if p.get("is_published", True))
    result["hidden_count"] = sum(1 for p in pages_list if not p.get("is_published", True))

    return JSONResponse(result)

@router.get("/api/admin/status")
async def get_visibility_status(request: Request):
    if not is_admin_server_request(request):
        raise HTTPException(status_code=404, detail="Not Found")

    v_map = page_visibility_service.get_visibility_map()
    return JSONResponse({"status": "success", "pages": v_map})

# ==============================================================================
# Nagaraj's Interview Activity & Schedules API Endpoints
# ==============================================================================

@router.get("/api/admin/interview-schedules")
async def get_interview_schedules(request: Request, date: Optional[str] = None):
    if not is_admin_server_request(request):
        raise HTTPException(status_code=404, detail="Not Found")

    schedules = interview_schedule_service.get_all_schedules()
    companies = interview_schedule_service.get_companies()
    rounds = interview_schedule_service.get_rounds()
    weekly = interview_schedule_service.get_weekly_data(date)

    return JSONResponse({
        "status": "success",
        "schedules": schedules,
        "companies": companies,
        "rounds": rounds,
        "weekly": weekly
    })

@router.get("/api/admin/interview-schedules/weekly")
async def get_interview_schedules_weekly(request: Request, date: Optional[str] = None):
    if not is_admin_server_request(request):
        raise HTTPException(status_code=404, detail="Not Found")

    weekly = interview_schedule_service.get_weekly_data(date)
    return JSONResponse({
        "status": "success",
        "weekly": weekly
    })

@router.get("/api/admin/interview-schedules/monthly")
async def get_interview_schedules_monthly(request: Request, month: Optional[str] = None):
    if not is_admin_server_request(request):
        raise HTTPException(status_code=404, detail="Not Found")

    monthly = interview_schedule_service.get_monthly_data(month)
    return JSONResponse({
        "status": "success",
        "monthly": monthly
    })

@router.post("/api/admin/interview-schedules/reorder")
async def reorder_interview_schedule_rounds(request: Request):
    if not is_admin_server_request(request):
        raise HTTPException(status_code=404, detail="Not Found")
    if not is_admin_request(request):
        return JSONResponse({"status": "error", "message": "Unauthorized. Please unlock with administrator passphrase."}, status_code=403)

    try:
        data = await request.json()
        company_name = data.get("company_name", "")
        ordered_ids = data.get("ordered_ids", [])
    except Exception as e:
        return JSONResponse({"status": "error", "message": f"Invalid payload: {str(e)}"}, status_code=400)

    updated = interview_schedule_service.reorder_rounds(company_name, ordered_ids)
    return JSONResponse({
        "status": "success",
        "message": f"Reordered rounds for {company_name}.",
        "rounds": updated
    })

@router.post("/api/admin/interview-schedules")
async def save_interview_schedule(request: Request):
    if not is_admin_server_request(request):
        raise HTTPException(status_code=404, detail="Not Found")
    if not is_admin_request(request):
        return JSONResponse({"status": "error", "message": "Unauthorized. Please unlock with administrator passphrase."}, status_code=403)

    try:
        data = await request.json()
    except Exception as e:
        return JSONResponse({"status": "error", "message": f"Invalid JSON payload: {str(e)}"}, status_code=400)

    saved = interview_schedule_service.save_schedule(data)
    weekly = interview_schedule_service.get_weekly_data()

    return JSONResponse({
        "status": "success",
        "message": "Interview schedule saved successfully.",
        "schedule": saved,
        "weekly": weekly
    })

@router.post("/api/admin/interview-schedules/status")
async def update_interview_schedule_status(request: Request):
    if not is_admin_server_request(request):
        raise HTTPException(status_code=404, detail="Not Found")
    if not is_admin_request(request):
        return JSONResponse({"status": "error", "message": "Unauthorized. Please unlock with administrator passphrase."}, status_code=403)

    try:
        data = await request.json()
    except Exception as e:
        return JSONResponse({"status": "error", "message": f"Invalid JSON payload: {str(e)}"}, status_code=400)

    sched_id = data.get("id") or data.get("schedule_id")
    status = data.get("status")
    cancellation_reason = data.get("cancellation_reason", "")
    has_transcript = data.get("has_transcript")
    transcript = data.get("transcript")
    youtube_url = data.get("youtube_url")

    if not sched_id or not status:
        return JSONResponse({"status": "error", "message": "Schedule ID and status are required."}, status_code=400)

    updated = interview_schedule_service.update_status(
        schedule_id=sched_id,
        status=status,
        cancellation_reason=cancellation_reason,
        has_transcript=has_transcript,
        transcript=transcript,
        youtube_url=youtube_url
    )

    if not updated:
        return JSONResponse({"status": "error", "message": "Schedule not found."}, status_code=404)

    weekly = interview_schedule_service.get_weekly_data()

    return JSONResponse({
        "status": "success",
        "message": f"Schedule status updated to {status}.",
        "schedule": updated,
        "weekly": weekly
    })

@router.post("/api/admin/interview-schedules/youtube")
async def update_interview_schedule_youtube(request: Request):
    if not is_admin_server_request(request):
        raise HTTPException(status_code=404, detail="Not Found")
    if not is_admin_request(request):
        return JSONResponse({"status": "error", "message": "Unauthorized. Please unlock with administrator passphrase."}, status_code=403)

    try:
        data = await request.json()
    except Exception as e:
        return JSONResponse({"status": "error", "message": f"Invalid JSON payload: {str(e)}"}, status_code=400)

    sched_id = data.get("id") or data.get("schedule_id")
    youtube_url = data.get("youtube_url", "")
    if not sched_id:
        return JSONResponse({"status": "error", "message": "Schedule ID is required."}, status_code=400)

    updated = interview_schedule_service.update_youtube_url(schedule_id=sched_id, youtube_url=youtube_url)
    if not updated:
        return JSONResponse({"status": "error", "message": "Schedule not found."}, status_code=404)

    return JSONResponse({
        "status": "success",
        "message": "YouTube recording link saved successfully.",
        "schedule": updated
    })

@router.delete("/api/admin/interview-schedules/{schedule_id}")
async def delete_interview_schedule(schedule_id: str, request: Request):
    if not is_admin_server_request(request):
        raise HTTPException(status_code=404, detail="Not Found")
    if not is_admin_request(request):
        return JSONResponse({"status": "error", "message": "Unauthorized. Please unlock with administrator passphrase."}, status_code=403)

    success = interview_schedule_service.delete_schedule(schedule_id)
    if not success:
        return JSONResponse({"status": "error", "message": "Schedule not found."}, status_code=404)

    return JSONResponse({
        "status": "success",
        "message": "Schedule deleted successfully.",
        "weekly": interview_schedule_service.get_weekly_data()
    })

@router.post("/api/admin/interview-schedules/upload")
async def upload_schedule_attachment(request: Request, file: UploadFile = File(...)):
    if not is_admin_server_request(request):
        raise HTTPException(status_code=404, detail="Not Found")
    if not is_admin_request(request):
        return JSONResponse({"status": "error", "message": "Unauthorized. Please unlock with administrator passphrase."}, status_code=403)

    try:
        content = await file.read()
        attachment = interview_schedule_service.save_attachment(
            file_bytes=content,
            original_filename=file.filename or "screenshot.png"
        )
        return JSONResponse({
            "status": "success",
            "message": "Screenshot uploaded losslessly.",
            "attachment": attachment
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": f"Upload failed: {str(e)}"}, status_code=500)

@router.get("/api/admin/interview-schedules/attachment/{filename}")
async def get_schedule_attachment(filename: str, request: Request):
    if not is_admin_server_request(request):
        raise HTTPException(status_code=404, detail="Not Found")

    file_path = interview_schedule_service.get_attachment_path(filename)
    if not file_path:
        raise HTTPException(status_code=404, detail="Attachment file not found")

    return FileResponse(path=str(file_path))

@router.get("/api/admin/interview-schedules/export/pdf")
async def export_interview_schedules_pdf(request: Request):
    if not is_admin_server_request(request):
        raise HTTPException(status_code=404, detail="Not Found")

    try:
        pdf_bytes = interview_schedule_service.generate_pdf_report()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="Nagaraj_Interview_Schedules_Report.pdf"'
            }
        )
    except Exception as e:
        return JSONResponse({"status": "error", "message": f"Failed to generate PDF report: {str(e)}"}, status_code=500)

@router.get("/api/admin/interview-schedules/export/editable")
async def export_interview_schedules_editable(request: Request, format: Optional[str] = "doc"):
    if not is_admin_server_request(request):
        raise HTTPException(status_code=404, detail="Not Found")

    try:
        doc_content = interview_schedule_service.generate_editable_report(format_type=format or "doc")
        if (format or "").lower() == "md":
            return Response(
                content=doc_content,
                media_type="text/markdown; charset=utf-8",
                headers={
                    "Content-Disposition": 'attachment; filename="Nagaraj_Interview_Schedules_Report.md"'
                }
            )
        else:
            return Response(
                content=doc_content,
                media_type="application/msword; charset=utf-8",
                headers={
                    "Content-Disposition": 'attachment; filename="Nagaraj_Interview_Schedules_Report.doc"'
                }
            )
    except Exception as e:
        return JSONResponse({"status": "error", "message": f"Failed to generate editable report: {str(e)}"}, status_code=500)
