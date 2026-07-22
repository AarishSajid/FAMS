"""
FastAPI dependencies for authentication and role-based authorization.
"""

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from enums import UserRole
from exceptions import UnauthorizedError, ForbiddenError
from services.auth_service import decode_access_token


async def get_current_user(
    authorization: str = Header(..., description="Bearer <accessToken>"),
    db: Session = Depends(get_db),
) -> User:
    """
    Decode the JWT from the Authorization header, look up the user in the
    database, and return the User object. Raises 401 if invalid.
    """
    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("Authorization header must start with 'Bearer '.")

    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)

    if payload is None:
        raise UnauthorizedError("Invalid or expired token.")

    user_id = payload.get("id")
    if not user_id:
        raise UnauthorizedError("Token payload missing 'id'.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UnauthorizedError("User not found.")

    if not user.isActive:
        raise ForbiddenError("User account is deactivated.")

    return user


def authorize(*allowed_roles: UserRole):
    """
    Returns a dependency that checks the current user's role against
    the allowed list. Usage:

        @router.get("/...", dependencies=[Depends(authorize(UserRole.ADMIN, UserRole.SCM))])
        def my_endpoint(...): ...

    Or inject as a parameter to also get the user object:

        def my_endpoint(user: User = Depends(authorize(UserRole.ADMIN))):
    """
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenError(
                f"Role '{current_user.role.value}' is not authorized. "
                f"Required: {', '.join(r.value for r in allowed_roles)}."
            )
        return current_user

    return _check
