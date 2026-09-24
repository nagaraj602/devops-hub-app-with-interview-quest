import os
import uvicorn
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import PORT, ADMIN_PORT, HOST, APP_DIR, BASE_DIR
from app.routes.question_bank_routes import router as question_bank_router
from app.routes.project_routes import router as project_router
from app.routes.training_routes import router as training_router
from app.routes.cheatsheet_routes import router as cheatsheet_router
from app.routes.sync_routes import router as sync_router
from app.routes.api_routes import router as api_router
from app.routes.admin_routes import router as admin_router, is_admin_request, is_admin_server_request
from app.services.page_visibility_service import page_visibility_service

# Lifespan startup pre-warm handler: pre-loads in-memory data caches before user traffic arrives
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from app.services.question_bank_service import question_bank_service
        from app.services.cheatsheet_service import cheatsheet_service
        from app.services.project_service import project_service
        question_bank_service.get_data()
        cheatsheet_service.get_data()
        project_service.get_project_data()
    except Exception as e:
        print(f"Lifespan pre-warm notice: {e}")
    yield

# Initialize FastAPI app
app = FastAPI(
    title="DevOps Knowledge Portal & Interview Hub",
    description="Universal DevOps Interview Questions, Project Architecture, Training Materials & Command Cheatsheets",
    version="1.0.12",
    lifespan=lifespan
)

# 1. GZip Compression Middleware (High Performance: Compresses responses > 500 bytes by ~90%)
app.add_middleware(GZipMiddleware, minimum_size=500)

# 2. Static Asset Caching Middleware (Sets 7-day browser cache headers for /static/ assets)
class StaticCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=604800, stale-while-revalidate=86400"
        return response

app.add_middleware(StaticCacheMiddleware)

# 3. Dedicated Admin Domain & Port Routing Middleware
# Ensures:
# - On public port (8926): /admin and /api/admin paths do NOT work (returns 404)
# - On dedicated admin port (9256): do NOT add /admin to URL; if /admin is visited, redirect to '/'
class AdminHostRoutingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        is_admin_entry = is_admin_server_request(request)

        # 1. On public port 8926 / non-admin domain: /admin and /api/admin paths must NOT work
        if not is_admin_entry:
            if request.url.path in ("/admin", "/admin/") or request.url.path.startswith("/admin/") or request.url.path.startswith("/api/admin"):
                return request.app.state.templates.TemplateResponse(
                    request=request,
                    name="404.html",
                    context={
                        "page_title": "Page Not Found",
                        "active_page": "404"
                    },
                    status_code=404
                )
            return await call_next(request)

        # 2. On dedicated admin port 9256 / admin.sidorea.shop:
        # Don't add /admin when admin dashboard itself is accessed at :9256. If /admin requested, redirect to '/'
        if request.url.path in ("/admin", "/admin/"):
            redirect_url = "/"
            if request.url.query:
                redirect_url += f"?{request.url.query}"
            return RedirectResponse(url=redirect_url, status_code=307)

        return await call_next(request)

app.add_middleware(AdminHostRoutingMiddleware)

# 4. Enable CORS for API queries
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates & Static Files setup
templates_dir = APP_DIR / "templates"
static_dir = APP_DIR / "static"

os.makedirs(templates_dir, exist_ok=True)
os.makedirs(static_dir, exist_ok=True)

templates = Jinja2Templates(directory=str(templates_dir))
# Register template global helpers for dynamic page visibility and auth
templates.env.globals["get_page_visibility"] = page_visibility_service.get_visibility_map
templates.env.globals["is_page_published"] = page_visibility_service.is_page_published
templates.env.globals["get_home_url"] = page_visibility_service.get_first_published_route
templates.env.globals["is_admin_request"] = is_admin_request
templates.env.globals["is_admin"] = False
app.state.templates = templates

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include Modular Feature Routers
app.include_router(question_bank_router)
app.include_router(project_router)
app.include_router(training_router)
app.include_router(cheatsheet_router)
app.include_router(sync_router)
app.include_router(api_router)
app.include_router(admin_router)

# Exception handler for 404
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse(
        request=request,
        name="404.html",
        context={
            "page_title": "Page Not Found",
            "active_page": "404"
        },
        status_code=404
    )

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
