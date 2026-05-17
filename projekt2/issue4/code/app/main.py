from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.tasks import router as tasks_router
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
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router)    # POST /register  POST /login
app.include_router(tasks_router)   # GET/POST /tasks  PUT/DELETE /tasks/{id}


# ---------------------------------------------------------------------------
# Startup — auto-create DB tables
# ---------------------------------------------------------------------------
@app.on_event("startup")
def on_startup() -> None:
    """Create all tables defined in ORM models if they don't exist yet."""
    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------
@app.get("/")
def root() -> dict:
    """Health-check endpoint."""
    return {"message": "Welcome to the Task Management API"}
