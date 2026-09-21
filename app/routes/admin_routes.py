import hmac
import hashlib
from fastapi import APIRouter, Request, Response, Form, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from typing import Optional, Dict, Any
from pydantic import BaseModel

from app.config import ADMIN_PORT, PORT, ADMIN_PASSWORD
from app.services.page_visibility_service import page_visibility_service

router = APIRouter()

COOKIE_NAME = "devops_hub_admin_auth"

def _get_expected_auth_token() -> str:
    return hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()

def is_admin_request(request: Request) -> bool:
    """
    Determines whether a request comes from an authenticated admin or the dedicated admin domain/port.
    """
    # 1. Check HTTP cookie
    cookie_val = request.cookies.get(COOKIE_NAME)
    if cookie_val and hmac.compare_digest(cookie_val, _get_expected_auth_token()):
        return True

    # 2. Check query parameter token
    param_token = request.query_params.get("token") or request.headers.get("X-Admin-Token")
    if param_token and (param_token == ADMIN_PASSWORD or hmac.compare_digest(param_token, _get_expected_auth_token())):
        return True

    # 3. Check if accessing via dedicated admin port (9256) on localhost or internal network
    host_header = (request.headers.get("host") or "").lower()
    port = request.url.port or (int(host_header.split(":")[1]) if ":" in host_header else None)
    if port == ADMIN_PORT:
        # Localhost on dedicated admin port is permitted direct access
        if "localhost" in host_header or "127.0.0.1" in host_header:
            return True

    return False

class VisibilityTogglePayload(BaseModel):
    page_key: str
    is_published: bool

@router.get("/admin", response_class=HTMLResponse)
async def admin_portal_view(request: Request):
    v_map = page_visibility_service.get_visibility_map()
    pages_list = list(v_map.values())
    
    published_count = sum(1 for p in pages_list if p.get("is_published", True))
    hidden_count = sum(1 for p in pages_list if not p.get("is_published", True))
    
    is_auth = is_admin_request(request)
    
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "page_title": "Admin Portal — Menu & Page Publisher",
            "active_page": "admin",
            "is_admin": True,
            "is_authenticated": is_auth,
            "pages": pages_list,
            "total_pages": len(pages_list),
            "published_count": published_count,
            "hidden_count": hidden_count,
            "admin_port": ADMIN_PORT,
            "main_port": PORT,
            "host_header": request.headers.get("host", "")
        }
    )

@router.post("/api/admin/login")
async def admin_login(request: Request, response: Response):
    try:
        data = await request.json()
        password = data.get("password", "")
    except Exception:
        password = ""

    if password == ADMIN_PASSWORD:
        token = _get_expected_auth_token()
        res = JSONResponse({"status": "success", "message": "Authentication successful. Controls unlocked."})
        res.set_cookie(
            key=COOKIE_NAME,
            value=token,
            max_age=86400 * 30,  # 30 days
            httponly=True,
            samesite="lax"
        )
        return res
    else:
        return JSONResponse({"status": "error", "message": "Invalid administrator passphrase."}, status_code=401)

@router.post("/api/admin/logout")
async def admin_logout(response: Response):
    res = JSONResponse({"status": "success", "message": "Logged out successfully."})
    res.delete_cookie(COOKIE_NAME)
    return res

@router.post("/api/admin/toggle-visibility")
async def toggle_visibility(payload: VisibilityTogglePayload, request: Request):
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
async def get_visibility_status():
    v_map = page_visibility_service.get_visibility_map()
    return JSONResponse({"status": "success", "pages": v_map})
