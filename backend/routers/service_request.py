"""
Service Request router — extends existing catalog with manager workflow + Redis queue.
"""

import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.service_request import Service, ServiceRequest
from models.farm import Farm
from models.user import User
from schemas.service_request import (
    CreateServiceRequest, CostRequest, ScheduleRequest, DeclineRequest,
    ServiceResponse, ServiceRequestResponse,
)
from dependencies import authorize, get_current_user
from enums import UserRole, ServiceRequestStatus
from exceptions import NotFoundError, ConflictError
from redis_client import enqueue_request, dequeue_request, get_request_queue

router = APIRouter(prefix="/service", tags=["Service Requests"])


# ── Public / Farmer endpoints ─────────────────────────────────

@router.get("/", response_model=list[ServiceResponse])
def get_service_catalogue(db: Session = Depends(get_db)):
    """List all active services (implements/drones)."""
    return db.query(Service).filter(Service.isActive == True).all()


@router.post("/{service_id}/request", response_model=ServiceRequestResponse)
def create_service_request(
    service_id: int,
    body: CreateServiceRequest,
    db: Session = Depends(get_db),
    user: User = Depends(authorize(UserRole.PROGRESSIVE_FARMER, UserRole.ADMIN)),
):
    """Farmer submits a new request."""
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise NotFoundError("Service", service_id)

    farm = db.query(Farm).filter(Farm.id == body.farmId).first()
    if not farm:
        raise NotFoundError("Farm", body.farmId)

    req = ServiceRequest(
        farmId=body.farmId,
        serviceId=service_id,
        notes=body.notes,
        serviceCenterId=farm.serviceCenterId,
        basePrice=service.rate,
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    # Enqueue in Redis if assigned to a center
    if req.serviceCenterId:
        enqueue_request(req.serviceCenterId, req.id, time.time())

    return req


@router.get("/{service_id}", response_model=ServiceResponse)
def get_service(service_id: int, db: Session = Depends(get_db)):
    """Get one service."""
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc:
        raise NotFoundError("Service", service_id)
    return svc


@router.get("/requests/farm/{farm_id}")
def get_farm_requests(
    farm_id: int,
    db: Session = Depends(get_db),
):
    """All service requests submitted by one farm (public, farmer-facing)."""
    reqs = db.query(ServiceRequest).filter(ServiceRequest.farmId == farm_id).all()
    return [
        {
            "id": r.id,
            "serviceId": r.serviceId,
            "status": r.status.value,
            "requestedAt": r.requestedAt.isoformat() if r.requestedAt else None,
            "service": {"id": r.service.id, "name": r.service.name, "rate": r.service.rate} if r.service else None,
        }
        for r in reqs
    ]


# ── Manager workflow endpoints ────────────────────────────────

@router.get("/requests/service-center/{center_id}")
def get_manager_queue(
    center_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(authorize(UserRole.SERVICE_CENTER_MANAGER, UserRole.ADMIN, UserRole.CHIEF_AGRONOMIST)),
):
    """Get the chronologically ordered queue of pending/active requests."""
    # 1. Get ordered IDs from Redis
    queued_ids = get_request_queue(center_id)
    if not queued_ids:
        return []

    # 2. Fetch from DB
    reqs = (
        db.query(ServiceRequest)
        .filter(ServiceRequest.id.in_([int(x) for x in queued_ids]))
        .all()
    )

    # 3. Sort to match Redis order
    req_map = {str(r.id): r for r in reqs}
    ordered_reqs = [req_map[qid] for qid in queued_ids if qid in req_map]

    # Convert to response dicts
    result = []
    for r in ordered_reqs:
        result.append({
            "id": r.id,
            "farmId": r.farmId,
            "serviceId": r.serviceId,
            "status": r.status.value,
            "notes": r.notes,
            "requestedAt": r.requestedAt.isoformat() if r.requestedAt else None,
            "basePrice": r.basePrice,
            "petrolCost": r.petrolCost,
            "totalCost": r.totalCost,
            "scheduledFor": r.scheduledFor.isoformat() if r.scheduledFor else None,
            "farm": {
                "id": r.farm.id,
                "farmer": r.farm.farmer,
                "village": r.farm.village,
            } if r.farm else None,
            "service": {
                "id": r.service.id,
                "name": r.service.name,
            } if r.service else None,
        })
    return result


@router.patch("/requests/{req_id}/cost")
def set_request_cost(
    req_id: int,
    body: CostRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(authorize(UserRole.SERVICE_CENTER_MANAGER, UserRole.ADMIN)),
):
    """Manager adds petrol/transport cost to a pending request."""
    req = db.query(ServiceRequest).filter(ServiceRequest.id == req_id).first()
    if not req:
        raise NotFoundError("ServiceRequest", req_id)

    if req.status != ServiceRequestStatus.PENDING:
        raise ConflictError("Can only set cost on PENDING requests.")

    req.petrolCost = body.petrolCost
    req.totalCost = (req.basePrice or 0.0) + body.petrolCost
    db.commit()
    return {"id": req.id, "petrolCost": req.petrolCost, "totalCost": req.totalCost}


@router.patch("/requests/{req_id}/schedule")
def schedule_request(
    req_id: int,
    body: ScheduleRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(authorize(UserRole.SERVICE_CENTER_MANAGER, UserRole.ADMIN)),
):
    """Schedule the service."""
    req = db.query(ServiceRequest).filter(ServiceRequest.id == req_id).first()
    if not req:
        raise NotFoundError("ServiceRequest", req_id)

    if req.status != ServiceRequestStatus.PENDING:
        raise ConflictError("Can only schedule PENDING requests.")

    req.scheduledFor = datetime.fromisoformat(body.scheduledFor)
    req.handledById = body.handledById
    req.status = ServiceRequestStatus.IN_PROGRESS
    db.commit()
    return {"id": req.id, "status": req.status.value, "scheduledFor": req.scheduledFor}


@router.patch("/requests/{req_id}/complete")
def complete_request(
    req_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(authorize(UserRole.SERVICE_CENTER_MANAGER, UserRole.ADMIN)),
):
    """Mark complete and remove from Redis queue."""
    req = db.query(ServiceRequest).filter(ServiceRequest.id == req_id).first()
    if not req:
        raise NotFoundError("ServiceRequest", req_id)

    req.status = ServiceRequestStatus.COMPLETED
    req.completedAt = datetime.now(timezone.utc)
    db.commit()

    if req.serviceCenterId:
        dequeue_request(req.serviceCenterId, req.id)

    return {"id": req.id, "status": req.status.value, "completedAt": req.completedAt}


@router.patch("/requests/{req_id}/decline")
def decline_request(
    req_id: int,
    body: DeclineRequest,
    db: Session = Depends(get_db),
    user: User = Depends(authorize(UserRole.SERVICE_CENTER_MANAGER, UserRole.ADMIN)),
):
    """Decline and remove from Redis queue."""
    req = db.query(ServiceRequest).filter(ServiceRequest.id == req_id).first()
    if not req:
        raise NotFoundError("ServiceRequest", req_id)

    req.status = ServiceRequestStatus.REJECTED
    req.declineReason = body.declineReason
    req.handledById = user.id
    db.commit()

    if req.serviceCenterId:
        dequeue_request(req.serviceCenterId, req.id)

    return {"id": req.id, "status": req.status.value, "declineReason": req.declineReason}
