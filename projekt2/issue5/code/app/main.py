from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

from app.api.auth import router as auth_router
from app.api.tasks import router as tasks_router
from app.api.recommend import router as recommend_router
from app.db.database import Base, engine
import app.models  # noqa: F401 — registers User + Task with Base.metadata

# ---------------------------------------------------------------------------
# FastAPI application instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Task Management API",
    description="REST API for task management with JWT auth and role-based access control.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS — allow all origins so the standalone HTML frontend can reach the API
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Static files — serves everything in app/static/ under /static
# ---------------------------------------------------------------------------
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router)      # POST /register   POST /login
app.include_router(tasks_router)     # GET/POST /tasks   PUT/DELETE /tasks/{id}
app.include_router(recommend_router) # GET /recommend

# ---------------------------------------------------------------------------
# Startup — auto-create DB tables
# ---------------------------------------------------------------------------
@app.on_event("startup")
def on_startup() -> None:
    """Create all tables defined in ORM models if they don't exist yet."""
    Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Frontend route — serves the HTML SPA
# ---------------------------------------------------------------------------
@app.get("/frontend", include_in_schema=False)
def frontend() -> FileResponse:
    """Serve the single-page frontend application."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------
@app.get("/")
def root() -> dict:
    """Health-check endpoint. Visit /frontend for the UI, /docs for the API."""
    return {
        "message": "Welcome to the Task Management API",
        "frontend": "/frontend",
        "docs": "/docs",
    }
