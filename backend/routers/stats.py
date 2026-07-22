"""
Stats router — Dashboard data feeds.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas.stats import KPIResponse, TrendItem, MapFarmItem
from services.stats_service import get_kpis, get_trends, get_map_data
from dependencies import authorize
from enums import UserRole

router = APIRouter(prefix="/stats", tags=["Dashboard Stats"])


@router.get("/service-center/{center_id}/kpis", response_model=KPIResponse)
def kpis(
    center_id: int,
    db: Session = Depends(get_db),
    _user=Depends(authorize(UserRole.SERVICE_CENTER_MANAGER, UserRole.CHIEF_AGRONOMIST, UserRole.ADMIN)),
):
    """Get the 4 KPI tiles for the dashboard."""
    return get_kpis(db, center_id)


@router.get("/service-center/{center_id}/trends", response_model=list[TrendItem])
def trends(
    center_id: int,
    cycles: int = 10,
    db: Session = Depends(get_db),
    _user=Depends(authorize(UserRole.SERVICE_CENTER_MANAGER, UserRole.CHIEF_AGRONOMIST, UserRole.ADMIN)),
):
    """Get historical trend data across cycles."""
    return get_trends(db, center_id, num_cycles=cycles)


@router.get("/service-center/{center_id}/map", response_model=list[MapFarmItem])
def map_data(
    center_id: int,
    db: Session = Depends(get_db),
    _user=Depends(authorize(UserRole.SERVICE_CENTER_MANAGER, UserRole.CHIEF_AGRONOMIST, UserRole.ADMIN, UserRole.FIELD_AGENT)),
):
    """Get farm locations and their current active case status for the map."""
    return get_map_data(db, center_id)
