from datetime import datetime, timedelta
from typing import Optional

import jwt  # pyjwt==2.6.0
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from werkzeug.security import check_password_hash, generate_password_hash  # werkzeug==2.3.0

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY

# ---------------------------------------------------------------------------
# OAuth2 scheme — FastAPI will extract the Bearer token from the
# Authorization header and pass it to functions that Depend on this.
# ---------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


# ---------------------------------------------------------------------------
# Password hashing  (werkzeug)
# ---------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password using werkzeug's PBKDF2-HMAC-SHA256.
    The result is safe to store in the database.
    """
    return generate_password_hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compare a plain-text password against its stored hash.
    Returns True if they match, False otherwise.
    """
    return check_password_hash(hashed_password, plain_password)


# ---------------------------------------------------------------------------
# JWT creation
# ---------------------------------------------------------------------------

def create_access_token(
    user_id: int,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Build and sign a JWT token that encodes the user's id and role.

    Payload keys
    ------------
    sub  : subject — the user's id (stored as string per JWT convention)
    role : user | admin — used for role-based access control
    exp  : expiry timestamp — token is rejected after this point
    """
    expire = datetime.utcnow() + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": str(user_id),   # subject = user id
        "role": role,
        "exp": expire,
    }
    # jwt.encode returns a str in pyjwt >= 2.x
    token: str = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


# ---------------------------------------------------------------------------
# JWT decoding / validation
# ---------------------------------------------------------------------------

def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    Raises HTTPException 401 if the token is expired or tampered with.
    Returns the decoded payload dict on success.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
