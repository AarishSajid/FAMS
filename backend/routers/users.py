"""
Users router — field agent availability, listing, and leaderboard.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.user import AvailabilityRequest
from services.leaderboard_service import get_agent_leaderboard
from dependencies import authorize, get_current_user
from enums import UserRole, FieldAgentAvailability
from exceptions import NotFoundError
from redis_client import invalidate_leaderboard_center

router = APIRouter(prefix="/users", tags=["Users / Field Agents"])


@router.patch("/{user_id}/availability")
def update_availability(
    user_id: str,
    body: AvailabilityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a field agent's availability status."""
    # Agents can update their own; managers/admins can update anyone
    if current_user.id != user_id and current_user.role not in (
        UserRole.ADMIN, UserRole.SERVICE_CENTER_MANAGER,
    ):
        from exceptions import ForbiddenError
        raise ForbiddenError("You can only update your own availability.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User", user_id)

    user.availabilityStatus = FieldAgentAvailability(body.availabilityStatus)
    db.commit()
    db.refresh(user)

    # Invalidate every leaderboard window for this agent's center + the global one
    invalidate_leaderboard_center(user.serviceCenterId)

    return {
        "id": user.id,
        "firstName": user.firstName,
        "lastName": user.lastName,
        "availabilityStatus": user.availabilityStatus.value if user.availabilityStatus else None,
    }


@router.get("/field-agents")
def list_field_agents(
    serviceCenterId: int | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(authorize(
        UserRole.ADMIN, UserRole.SERVICE_CENTER_MANAGER, UserRole.CHIEF_AGRONOMIST,
    )),
):
    """List field agents, optionally filtered by service center and availability."""
    query = db.query(User).filter(User.role == UserRole.FIELD_AGENT)

    if serviceCenterId is not None:
        query = query.filter(User.serviceCenterId == serviceCenterId)
    if status:
        query = query.filter(User.availabilityStatus == status)

    agents = query.all()
    return [
        {
            "id": a.id,
            "firstName": a.firstName,
            "lastName": a.lastName,
            "email": a.email,
            "availabilityStatus": a.availabilityStatus.value if a.availabilityStatus else None,
            "serviceCenterId": a.serviceCenterId,
            "isActive": a.isActive,
            "_count": {
                "assignedCases": len(a.assignedAdvisoryCases),
                "verifications": len(a.verifications),
            },
        }
        for a in agents
    ]


@router.get("/leaderboard")
def leaderboard(
    serviceCenterId: int | None = Query(None),
    sinceDays: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    _user: User = Depends(authorize(
        UserRole.ADMIN, UserRole.SERVICE_CENTER_MANAGER, UserRole.CHIEF_AGRONOMIST,
    )),
):
    """Agent leaderboard — cached in Redis for 1 hour."""
    return get_agent_leaderboard(db, service_center_id=serviceCenterId, since_days=sinceDays)
