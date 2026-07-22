"""
Service Center router — CRUD + farm/agent assignment.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.service_center import ServiceCenter, District
from models.farm import Farm
from models.user import User
from schemas.service_center import (
    ServiceCenterCreate, ServiceCenterUpdate,
    AssignFarmsRequest, AssignAgentsRequest,
    ServiceCenterResponse, ServiceCenterDetail,
)
from dependencies import authorize
from enums import UserRole
from exceptions import NotFoundError

router = APIRouter(prefix="/service-center", tags=["Service Centers"])


@router.post("/", response_model=ServiceCenterResponse)
def create_service_center(
    body: ServiceCenterCreate,
    db: Session = Depends(get_db),
    _user=Depends(authorize(UserRole.ADMIN)),
):
    center = ServiceCenter(**body.model_dump())
    db.add(center)
    db.commit()
    db.refresh(center)
    return center


@router.get("/")
def list_service_centers(
    db: Session = Depends(get_db),
    _user=Depends(authorize(UserRole.ADMIN, UserRole.SERVICE_CENTER_MANAGER, UserRole.CHIEF_AGRONOMIST)),
):
    centers = db.query(ServiceCenter).all()
    results = []
    for c in centers:
        district = db.query(District).filter(District.id == c.districtId).first() if c.districtId else None
        results.append({
            "id": c.id,
            "name": c.name,
            "region": c.region,
            "districtId": c.districtId,
            "phone": c.phone,
            "district": {"id": district.id, "name": district.name} if district else None,
            "_count": {
                "farms": len(c.farms),
                "users": len(c.users),
                "advisoryCases": len(c.advisoryCases),
            },
        })
    return results


@router.get("/{center_id}")
def get_service_center(
    center_id: int,
    db: Session = Depends(get_db),
    _user=Depends(authorize(UserRole.ADMIN, UserRole.SERVICE_CENTER_MANAGER, UserRole.CHIEF_AGRONOMIST)),
):
    center = db.query(ServiceCenter).filter(ServiceCenter.id == center_id).first()
    if not center:
        raise NotFoundError("ServiceCenter", center_id)

    district = db.query(District).filter(District.id == center.districtId).first() if center.districtId else None

    return {
        "id": center.id,
        "name": center.name,
        "region": center.region,
        "districtId": center.districtId,
        "phone": center.phone,
        "district": {"id": district.id, "name": district.name} if district else None,
        "farms": [
            {
                "id": f.id, "farmer": f.farmer, "phone": f.phone, "village": f.village,
                "lat": f.lat, "lon": f.lon, "acres": f.acres, 
                "crop": f.fieldCrops[0].crop if f.fieldCrops else None, 
                "variety": f.fieldCrops[0].variety if f.fieldCrops else None,
                "irrigation": ["Canal"], 
                "sowDate": f.fieldCrops[0].sowDate.isoformat() if f.fieldCrops and f.fieldCrops[0].sowDate else None, 
                "harvestDate": f.fieldCrops[0].harvestDate.isoformat() if f.fieldCrops and f.fieldCrops[0].harvestDate else None, 
                "yieldExpected": None
            }
            for f in center.farms
        ],
        "users": [
            {
                "id": u.id, "firstName": u.firstName, "lastName": u.lastName,
                "role": u.role.value if hasattr(u.role, 'value') else u.role,
                "availabilityStatus": u.availabilityStatus.value if u.availabilityStatus and hasattr(u.availabilityStatus, 'value') else u.availabilityStatus,
            }
            for u in center.users
        ],
    }


@router.put("/{center_id}", response_model=ServiceCenterResponse)
def update_service_center(
    center_id: int,
    body: ServiceCenterUpdate,
    db: Session = Depends(get_db),
    _user=Depends(authorize(UserRole.ADMIN)),
):
    center = db.query(ServiceCenter).filter(ServiceCenter.id == center_id).first()
    if not center:
        raise NotFoundError("ServiceCenter", center_id)

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(center, key, value)

    db.commit()
    db.refresh(center)
    return center


@router.patch("/{center_id}/farms")
def assign_farms(
    center_id: int,
    body: AssignFarmsRequest,
    db: Session = Depends(get_db),
    _user=Depends(authorize(UserRole.ADMIN, UserRole.SERVICE_CENTER_MANAGER)),
):
    center = db.query(ServiceCenter).filter(ServiceCenter.id == center_id).first()
    if not center:
        raise NotFoundError("ServiceCenter", center_id)

    updated = (
        db.query(Farm)
        .filter(Farm.id.in_(body.farmIds))
        .update({Farm.serviceCenterId: center_id}, synchronize_session="fetch")
    )
    db.commit()

    return {"message": "Farms assigned to service center", "serviceCenterId": center_id, "farmsUpdated": updated}


@router.patch("/{center_id}/agents")
def assign_agents(
    center_id: int,
    body: AssignAgentsRequest,
    db: Session = Depends(get_db),
    _user=Depends(authorize(UserRole.ADMIN, UserRole.SERVICE_CENTER_MANAGER)),
):
    center = db.query(ServiceCenter).filter(ServiceCenter.id == center_id).first()
    if not center:
        raise NotFoundError("ServiceCenter", center_id)

    updated = (
        db.query(User)
        .filter(User.id.in_(body.userIds))
        .update({User.serviceCenterId: center_id}, synchronize_session="fetch")
    )
    db.commit()

    return {"message": "Users assigned to service center", "serviceCenterId": center_id, "usersUpdated": updated}
