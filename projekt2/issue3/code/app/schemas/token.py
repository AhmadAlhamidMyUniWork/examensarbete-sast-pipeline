from pydantic import BaseModel


class Token(BaseModel):
    """Response body returned after a successful login."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """
    Decoded contents of a JWT token.
    Used internally by the get_current_user dependency.
    """
    user_id: int
    role: str
