from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import engine, Base
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
# CORS — allow all origins during development
# Replace "*" with the frontend's actual origin in production
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Startup event — create all tables if they don't exist yet
# ---------------------------------------------------------------------------
@app.on_event("startup")
def on_startup() -> None:
    """
    Called once when the server starts.
    Base.metadata.create_all() inspects all registered ORM models
    (User, Task) and issues CREATE TABLE IF NOT EXISTS for each one.
    """
    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------
@app.get("/")
def root() -> dict:
    """Health-check / welcome endpoint."""
    return {"message": "Welcome to the Task Management API"}
