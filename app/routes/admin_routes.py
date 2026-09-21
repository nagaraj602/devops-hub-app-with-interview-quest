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
    """
    # Admin privileges can only be exercised on the dedicated admin port / admin domain
    if not is_admin_server_request(request):
        return False

    # Localhost or 127.0.0.1 on the dedicated admin port is automatically authorized
    host_header = (request.headers.get("host") or "").lower()
    if "localhost" in host_header or "127.0.0.1" in host_header:
        return True

    # 1. Check HTTP cookie
    cookie_val = request.cookies.get(COOKIE_NAME)
    if cookie_val and hmac.compare_digest(cookie_val, _get_expected_auth_token()):
        return True

    # 2. Check query parameter token or header
    param_token = request.query_params.get("token") or request.headers.get("X-Admin-Token")
    if param_token and (param_token == ADMIN_PASSWORD or hmac.compare_digest(param_token, _get_expected_auth_token())):
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
async def admin_logout(request: Request, response: Response):
    if not is_admin_server_request(request):
        raise HTTPException(status_code=404, detail="Not Found")

    res = JSONResponse({"status": "success", "message": "Logged out successfully."})
    res.delete_cookie(COOKIE_NAME)
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
