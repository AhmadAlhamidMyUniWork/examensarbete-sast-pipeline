from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI application
app = FastAPI(
    title="Task Management API",
    description="A REST API for managing tasks with JWT authentication and role-based access control.",
    version="1.0.0",
)

# CORS configuration — allows requests from any origin during development.
# In production, replace "*" with the actual frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Root endpoint — health check / welcome message."""
    return {"message": "Welcome to the Task Management API"}
