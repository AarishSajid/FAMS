"""
Auth router — POST /auth/login, GET /auth/me
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.auth import LoginRequest, LoginResponse, UserResponse, MeResponse, RefreshRequest
from services.auth_service import verify_password, create_access_token, create_refresh_token, decode_access_token
from dependencies import get_current_user
from exceptions import UnauthorizedError

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Log in with email or username. Returns JWT tokens."""
    if not body.email and not body.username:
        raise UnauthorizedError("Provide either email or username.")

    query = db.query(User)
    if body.email:
        query = query.filter(User.email == body.email)
    else:
        query = query.filter(User.username == body.username)

    user = query.first()
    if not user:
        raise UnauthorizedError("Invalid credentials.")

    if not verify_password(body.password, user.password):
        raise UnauthorizedError("Invalid credentials.")

    if not user.isActive:
        raise UnauthorizedError("Account is deactivated.")

    # Update last login
    user.lastLogin = datetime.now(timezone.utc)
    db.commit()

    token_data = {"id": user.id, "role": user.role.value if hasattr(user.role, 'value') else user.role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return LoginResponse(
        message="Login successful",
        user=UserResponse.model_validate(user),
        accessToken=access_token,
        refreshToken=refresh_token,
    )


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)):
    """Returns the identity of the currently logged-in user."""
    return MeResponse.model_validate(current_user)


@router.post("/refresh")
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    """Exchanges a valid refresh token for a new access+refresh token pair."""
    payload = decode_access_token(body.refreshToken)
    if not payload or payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid or expired refresh token")
    
    user_id = payload.get("id")
    if not user_id:
        raise UnauthorizedError("Invalid token payload")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.isActive:
        raise UnauthorizedError("User inactive or not found")
        
    token_data = {"id": user.id, "role": user.role.value if hasattr(user.role, 'value') else user.role}
    new_access = create_access_token(token_data)
    new_refresh = create_refresh_token(token_data)
    
    return {
        "accessToken": new_access,
        "refreshToken": new_refresh
    }
