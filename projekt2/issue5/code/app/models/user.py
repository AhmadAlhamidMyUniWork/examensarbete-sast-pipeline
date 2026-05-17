import enum
from sqlalchemy import Column, Enum, Integer, String
from sqlalchemy.orm import relationship
from app.db.database import Base


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class User(Base):
    __tablename__ = "users"
    id       = Column(Integer, primary_key=True, index=True)
    email    = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role     = Column(Enum(UserRole), default=UserRole.user, nullable=False)
    tasks    = relationship("Task", back_populates="owner", cascade="all, delete-orphan")
