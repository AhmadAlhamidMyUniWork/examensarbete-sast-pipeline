# Task Management API

A backend REST API built with FastAPI, SQLAlchemy, and JWT authentication.

## Project Structure

```
app/
├── api/        # Route handlers (endpoints)
├── core/       # Config, security helpers (JWT, hashing)
├── db/         # Database engine and session setup
├── models/     # SQLAlchemy ORM models
└── main.py     # FastAPI app instance + middleware
requirements.txt
README.md
```

## Setup

### 1. Create and activate virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the development server

```bash
uvicorn app.main:app --reload
```

The API will be available at: http://127.0.0.1:8000

Interactive docs: http://127.0.0.1:8000/docs

## Endpoints (planned)

| Method | Path           | Description                  |
|--------|----------------|------------------------------|
| GET    | /              | Health check                 |
| POST   | /register      | Create a new user            |
| POST   | /login         | Authenticate and get JWT     |
| GET    | /tasks         | List tasks (auth required)   |
| POST   | /tasks         | Create a task (auth required)|
| PUT    | /tasks/{id}    | Update a task (auth required)|
| GET    | /recommend     | AI task recommendations      |
