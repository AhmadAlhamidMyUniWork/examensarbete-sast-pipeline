import enum
from sqlalchemy import Column, Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.db.database import Base


class TaskPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class TaskStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    done = "done"


class Task(Base):
    __tablename__ = "tasks"
    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date    = Column(Date, nullable=True)
    priority    = Column(Enum(TaskPriority), default=TaskPriority.medium, nullable=False)
    status      = Column(Enum(TaskStatus), default=TaskStatus.pending, nullable=False)
    owner_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner       = relationship("User", back_populates="tasks")
