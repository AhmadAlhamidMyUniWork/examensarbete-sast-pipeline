from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import decode_access_token, oauth2_scheme
from app.db.database import get_db
from app.models.user import User
from app.schemas.token import TokenData


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency — resolves the JWT Bearer token from the request header,
    validates it, and returns the corresponding User ORM object.

    Usage in a protected endpoint:
        @app.get("/me")
        def me(current_user: User = Depends(get_current_user)):
            ...
    """
    # Decode & validate the token (raises 401 on failure)
    payload = decode_access_token(token)

    # Extract claims
    user_id: str | None = payload.get("sub")
    role: str | None = payload.get("role")

    if user_id is None or role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing required fields",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = TokenData(user_id=int(user_id), role=role)

    # Look up the user in the database
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User belonging to this token no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency — same as get_current_user but additionally enforces
    that the authenticated user has the 'admin' role.

    Usage:
        @app.delete("/users/{id}")
        def delete_user(admin: User = Depends(get_current_admin)):
            ...
    """
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user
