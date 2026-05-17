from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Request schemas (incoming data from the client)
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    """Payload expected by POST /register."""
    email: EmailStr
    password: str = Field(..., min_length=6, description="Minimum 6 characters")


class UserLogin(BaseModel):
    """Payload expected by POST /login."""
    email: EmailStr
    password: str


# ---------------------------------------------------------------------------
# Response schemas (data returned to the client)
# ---------------------------------------------------------------------------

class UserOut(BaseModel):
    """Safe user representation — never exposes the hashed password."""
    id: int
    email: EmailStr
    role: str

    class Config:
        # Allow SQLAlchemy ORM objects to be serialised directly
        orm_mode = True
