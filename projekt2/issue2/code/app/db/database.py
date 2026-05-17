from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite database file will be created in the project root
SQLALCHEMY_DATABASE_URL = "sqlite:///./tasks.db"

# check_same_thread=False is required for SQLite to work with FastAPI's
# async request handling (multiple threads may share the same connection)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Each request gets its own session; autocommit/autoflush are disabled
# so we control transactions explicitly
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All ORM models inherit from this Base — SQLAlchemy uses it to track
# which tables to create / migrate
Base = declarative_base()


# ---------------------------------------------------------------------------
# Dependency — used with FastAPI's Depends() to inject a DB session
# ---------------------------------------------------------------------------
def get_db():
    """Yield a database session and ensure it is closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Raw SQL example (acceptance criterion)
# ---------------------------------------------------------------------------
def get_all_users_raw(db) -> list[dict]:
    """
    Fetch all users using a raw SQL query.
    Demonstrates how to run raw SQL alongside the ORM.
    Returns a list of dicts with id, email, and role columns.
    """
    result = db.execute(text("SELECT id, email, role FROM users"))
    # SQLAlchemy 1.4 rows support _mapping for easy dict conversion
    return [dict(row._mapping) for row in result]


def get_tasks_by_status_raw(db, status: str) -> list[dict]:
    """
    Fetch tasks filtered by status using a raw parameterised SQL query.
    Using :param syntax prevents SQL injection.
    """
    result = db.execute(
        text("SELECT id, title, priority, status, owner_id FROM tasks WHERE status = :status"),
        {"status": status},
    )
    return [dict(row._mapping) for row in result]
