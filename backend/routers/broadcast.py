"""
Broadcast router — push messages to farmers.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.broadcast import Broadcast
from models.user import User
from schemas.broadcast import BroadcastCreate, BroadcastResponse
from dependencies import authorize, get_current_user
from enums import UserRole, BroadcastCategory
from exceptions import NotFoundError

router = APIRouter(prefix="/broadcast", tags=["Broadcasts"])


@router.post("/", response_model=BroadcastResponse)
def create_broadcast(
    body: BroadcastCreate,
    db: Session = Depends(get_db),
    user: User = Depends(authorize(UserRole.CHIEF_AGRONOMIST, UserRole.SERVICE_CENTER_MANAGER, UserRole.ADMIN)),
):
    """Create a new broadcast message."""
    b = Broadcast(
        title=body.title,
        text=body.text,
        category=BroadcastCategory(body.category) if body.category else None,
        districtId=body.districtId,
        serviceCenterId=body.serviceCenterId,
        createdById=user.id,
    )
    db.add(b)
    db.commit()
    db.refresh(b)

    return db.query(Broadcast).options(joinedload(Broadcast.district)).filter(Broadcast.id == b.id).first()


@router.get("/", response_model=list[BroadcastResponse])
def list_broadcasts(
    districtId: int | None = None,
    serviceCenterId: int | None = None,
    db: Session = Depends(get_db),
):
    """List broadcasts, optionally filtered."""
    query = db.query(Broadcast).options(joinedload(Broadcast.district))

    if districtId:
        query = query.filter(Broadcast.districtId == districtId)
    if serviceCenterId:
        query = query.filter(Broadcast.serviceCenterId == serviceCenterId)

    return query.order_by(Broadcast.createdAt.desc()).all()


@router.delete("/{broadcast_id}")
def delete_broadcast(
    broadcast_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(authorize(UserRole.CHIEF_AGRONOMIST, UserRole.SERVICE_CENTER_MANAGER, UserRole.ADMIN)),
):
    """Retract a broadcast."""
    b = db.query(Broadcast).filter(Broadcast.id == broadcast_id).first()
    if not b:
        raise NotFoundError("Broadcast", broadcast_id)

    db.delete(b)
    db.commit()
    return {"message": "Broadcast deleted"}
