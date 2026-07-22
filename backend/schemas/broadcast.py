"""Pydantic schemas for broadcast endpoints."""

from pydantic import BaseModel
from datetime import datetime


class BroadcastCreate(BaseModel):
    title: str
    text: str
    category: str | None = None
    districtId: int | None = None
    serviceCenterId: int | None = None


class DistrictBrief(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class BroadcastResponse(BaseModel):
    id: int
    title: str
    text: str | None = None
    category: str | None = None
    districtId: int | None = None
    serviceCenterId: int | None = None
    createdById: str | None = None
    validFrom: datetime | None = None
    validTo: datetime | None = None
    district: DistrictBrief | None = None
    model_config = {"from_attributes": True}
