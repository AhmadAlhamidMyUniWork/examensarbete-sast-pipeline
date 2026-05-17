import enum

from sqlalchemy import Column, Enum, Integer, String
from sqlalchemy.orm import relationship

from app.db.database import Base


class UserRole(str, enum.Enum):
    """Allowed roles for a user account."""
    user = "user"
    admin = "admin"


class User(Base):
    """
    Represents an application user.

    Columns
    -------
    id       : auto-incremented primary key
    email    : unique login identifier
    password : bcrypt/werkzeug hashed value — never stored in plain text
    role     : 'user' (default) or 'admin' — drives access control
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)          # hashed — see core/security.py
    role = Column(
        Enum(UserRole),
        default=UserRole.user,
        nullable=False,
    )

    # One user → many tasks (bidirectional via back_populates)
    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
