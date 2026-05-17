from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.database import get_db
from app.models.user import User, UserRole
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserLogin, UserOut

router = APIRouter(tags=["Authentication"])


# ---------------------------------------------------------------------------
# POST /register
# ---------------------------------------------------------------------------
@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(user_data: UserCreate, db: Session = Depends(get_db)) -> UserOut:
    """
    Create a new user account.

    - Email must be unique
    - Password is hashed before storage (werkzeug PBKDF2)
    - New accounts are always assigned the 'user' role by default
    """
    # Check for duplicate email
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )

    # Hash the password — never store plain text
    hashed_pw = hash_password(user_data.password)

    new_user = User(
        email=user_data.email,
        password=hashed_pw,
        role=UserRole.user,        # default role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)           # reload to get the auto-generated id

    return new_user


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------
@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate and receive a JWT token",
)
def login(credentials: UserLogin, db: Session = Depends(get_db)) -> Token:
    """
    Validate email + password and return a signed JWT.

    The token payload contains:
    - `sub`  : user id (string)
    - `role` : 'user' or 'admin'
    - `exp`  : expiry timestamp

    Pass the returned token as:
        Authorization: Bearer <token>
    on all protected endpoints.
    """
    # Look up user by email
    user = db.query(User).filter(User.email == credentials.email).first()

    # Use a generic error message to avoid leaking whether the email exists
    if not user or not verify_password(credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Build JWT with user_id + role embedded in the payload
    access_token = create_access_token(
        user_id=user.id,
        role=user.role.value,   # convert Enum → plain string
    )

    return Token(access_token=access_token, token_type="bearer")
