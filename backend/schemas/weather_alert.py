"""Pydantic schemas for weather alert endpoints."""

from pydantic import BaseModel
from datetime import datetime


class WeatherAlertCreate(BaseModel):
    districtId: int
    alertType: str
    severity: str
    headline: str | None = None
    message: str
    validFrom: str
    validTo: str | None = None


class WeatherAlertUpdate(BaseModel):
    alertType: str | None = None
    severity: str | None = None
    headline: str | None = None
    message: str | None = None
    validFrom: str | None = None
    validTo: str | None = None


class WeatherAlertResponse(BaseModel):
    id: int
    districtId: int
    alertType: str
    severity: str
    headline: str | None = None
    message: str
    validFrom: datetime | None = None
    validTo: datetime | None = None
    source: str | None = None
    model_config = {"from_attributes": True}
