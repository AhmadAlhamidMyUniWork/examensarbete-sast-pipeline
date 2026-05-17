from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./tasks.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Yield a database session and ensure it is closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_all_users_raw(db) -> list[dict]:
    """Raw SQL example — fetch all users."""
    result = db.execute(text("SELECT id, email, role FROM users"))
    return [dict(row._mapping) for row in result]


def get_tasks_by_status_raw(db, status: str) -> list[dict]:
    """Raw SQL example — fetch tasks filtered by status."""
    result = db.execute(
        text("SELECT id, title, priority, status, owner_id FROM tasks WHERE status = :status"),
        {"status": status},
    )
    return [dict(row._mapping) for row in result]
