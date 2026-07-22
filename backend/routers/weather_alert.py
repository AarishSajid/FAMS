"""
Weather Alert router.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.weather_alert import WeatherAlert
from models.user import User
from schemas.weather_alert import WeatherAlertCreate, WeatherAlertUpdate, WeatherAlertResponse
from dependencies import authorize
from enums import UserRole, AdvisorySeverity
from exceptions import NotFoundError

router = APIRouter(prefix="/weather-alert", tags=["Weather Alerts"])


@router.post("/", response_model=WeatherAlertResponse)
def create_weather_alert(
    body: WeatherAlertCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(authorize(UserRole.CHIEF_AGRONOMIST, UserRole.SERVICE_CENTER_MANAGER, UserRole.ADMIN)),
):
    """Manager creates a manual weather alert."""
    alert = WeatherAlert(
        districtId=body.districtId,
        alertType=body.alertType,
        severity=AdvisorySeverity(body.severity),
        headline=body.headline,
        message=body.message,
        validFrom=datetime.fromisoformat(body.validFrom),
        validTo=datetime.fromisoformat(body.validTo) if body.validTo else None,
        source="manual",
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.get("/district/{district_id}", response_model=list[WeatherAlertResponse])
def get_district_alerts(
    district_id: int,
    db: Session = Depends(get_db),
):
    """Get active alerts for a district."""
    return db.query(WeatherAlert).filter(WeatherAlert.districtId == district_id).order_by(WeatherAlert.validFrom.desc()).all()


@router.patch("/{alert_id}", response_model=WeatherAlertResponse)
def update_weather_alert(
    alert_id: int,
    body: WeatherAlertUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(authorize(UserRole.CHIEF_AGRONOMIST, UserRole.SERVICE_CENTER_MANAGER, UserRole.ADMIN)),
):
    """Update an existing alert."""
    alert = db.query(WeatherAlert).filter(WeatherAlert.id == alert_id).first()
    if not alert:
        raise NotFoundError("WeatherAlert", alert_id)

    update_data = body.model_dump(exclude_unset=True)
    if "severity" in update_data and update_data["severity"]:
        update_data["severity"] = AdvisorySeverity(update_data["severity"])
    if "validFrom" in update_data and update_data["validFrom"]:
        update_data["validFrom"] = datetime.fromisoformat(update_data["validFrom"])
    if "validTo" in update_data and update_data["validTo"]:
        update_data["validTo"] = datetime.fromisoformat(update_data["validTo"])

    for key, value in update_data.items():
        setattr(alert, key, value)

    db.commit()
    db.refresh(alert)
    return alert


@router.delete("/{alert_id}")
def delete_weather_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(authorize(UserRole.CHIEF_AGRONOMIST, UserRole.SERVICE_CENTER_MANAGER, UserRole.ADMIN)),
):
    """Delete an alert."""
    alert = db.query(WeatherAlert).filter(WeatherAlert.id == alert_id).first()
    if not alert:
        raise NotFoundError("WeatherAlert", alert_id)

    db.delete(alert)
    db.commit()
    return {"message": "Weather alert deleted"}
