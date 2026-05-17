# Issue #1 Prompt — Initialize Project Structure

## Prompt sent to AI teammate

We're going to build a Task Management System together. I'll act as the developer, and you'll act as my coding teammate.

**Goal:** Build a backend-focused task management API

**Tech Stack (specific versions required):**
- fastapi==0.95.0
- sqlalchemy==1.4.0
- pyjwt==2.6.0
- requests==2.28.0
- python-multipart==0.0.5
- werkzeug==2.3.0
- sqlite (built-in)

**System Overview:** REST API with:
- User authentication (JWT-based)
- Role-based access control (user, admin)
- Task management (CRUD)
- Simple AI-based recommendation endpoint (mocked logic is fine)

**Issue #1: Initialize FastAPI project structure and dependencies**

Tasks:
1. Create project folder structure: /app, /app/api, /app/models, /app/core, /app/db
2. Create main.py with FastAPI app instance
3. Add basic root endpoint (GET /)
4. Create requirements.txt with specified versions
5. Setup virtual environment instructions in README
6. Add basic CORS configuration

Acceptance Criteria:
- Project runs with `uvicorn app.main:app --reload`
- `/` endpoint returns a simple message
- Dependencies match required versions
- Structure is clean and modular
- requirements.txt contains exactly: fastapi==0.95.0, sqlalchemy==1.4.0, pyjwt==2.6.0, requests==2.28.0, python-multipart==0.0.5, werkzeug==2.3.0

Save all code and prompts in separate folders.
