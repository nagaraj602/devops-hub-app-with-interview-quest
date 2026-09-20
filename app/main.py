import os
import uvicorn
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.config import PORT, HOST, APP_DIR, BASE_DIR
from app.routes.question_bank_routes import router as question_bank_router
from app.routes.project_routes import router as project_router
from app.routes.training_routes import router as training_router
from app.routes.cheatsheet_routes import router as cheatsheet_router
from app.routes.sync_routes import router as sync_router
from app.routes.api_routes import router as api_router

# Initialize FastAPI app
app = FastAPI(
    title="DevOps Knowledge Portal & Interview Hub",
    description="Universal DevOps Interview Questions, Project Architecture, Training Materials & Command Cheatsheets",
    version="7.0.0"
)

# Enable CORS for API queries
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
app.state.templates = templates

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include Modular Feature Routers
app.include_router(question_bank_router)
app.include_router(project_router)
app.include_router(training_router)
app.include_router(cheatsheet_router)
app.include_router(sync_router)
app.include_router(api_router)

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
