import enum

from sqlalchemy import Column, Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class TaskPriority(str, enum.Enum):
    """Priority levels for a task."""
    low = "low"
    medium = "medium"
    high = "high"


class TaskStatus(str, enum.Enum):
    """Lifecycle states for a task."""
    pending = "pending"
    in_progress = "in_progress"
    done = "done"


class Task(Base):
    """
    Represents a task owned by a user.

    Columns
    -------
    id          : auto-incremented primary key
    title       : short task name (required)
    description : optional longer description
    due_date    : optional deadline (DATE type)
    priority    : low | medium (default) | high
    status      : pending (default) | in_progress | done
    owner_id    : FK → users.id — the user who created this task
    """

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(Date, nullable=True)
    priority = Column(
        Enum(TaskPriority),
        default=TaskPriority.medium,
        nullable=False,
    )
    status = Column(
        Enum(TaskStatus),
        default=TaskStatus.pending,
        nullable=False,
    )
    # FK to users table — task is deleted if its owner is deleted (cascade)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Many tasks → one user (bidirectional)
    owner = relationship("User", back_populates="tasks")

    def __repr__(self) -> str:
        return f"<Task id={self.id} title={self.title!r} status={self.status}>"
