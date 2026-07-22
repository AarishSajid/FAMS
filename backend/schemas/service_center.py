"""Pydantic schemas for service center endpoints."""

from pydantic import BaseModel
from datetime import datetime


# ── Request schemas ───────────────────────────────────────────

class ServiceCenterCreate(BaseModel):
    name: str
    region: str | None = None
    districtId: int | None = None
    phone: str | None = None


class ServiceCenterUpdate(BaseModel):
    name: str | None = None
    region: str | None = None
    districtId: int | None = None
    phone: str | None = None


class AssignFarmsRequest(BaseModel):
    farmIds: list[int]


class AssignAgentsRequest(BaseModel):
    userIds: list[str]


# ── Response schemas ──────────────────────────────────────────

class DistrictBrief(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class FarmBrief(BaseModel):
    id: int
    farmer: str | None = None
    phone: str | None = None
    village: str | None = None
    lat: float | None = None
    lon: float | None = None
    acres: float | None = None
    crop: str | None = None
    variety: str | None = None
    irrigation: list[str] | None = None
    sowDate: str | None = None
    harvestDate: str | None = None
    yieldExpected: float | None = None
    model_config = {"from_attributes": True}


class UserBrief(BaseModel):
    id: str
    firstName: str | None = None
    lastName: str | None = None
    role: str | None = None
    availabilityStatus: str | None = None
    model_config = {"from_attributes": True}


class ServiceCenterResponse(BaseModel):
    id: int
    name: str
    region: str | None = None
    districtId: int | None = None
    phone: str | None = None
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
    model_config = {"from_attributes": True}


class ServiceCenterListItem(BaseModel):
    id: int
    name: str
    region: str | None = None
    districtId: int | None = None
    phone: str | None = None
    district: DistrictBrief | None = None
    _count: dict | None = None
    model_config = {"from_attributes": True}


class ServiceCenterDetail(BaseModel):
    id: int
    name: str
    region: str | None = None
    districtId: int | None = None
    phone: str | None = None
    district: DistrictBrief | None = None
    farms: list[FarmBrief] = []
    users: list[UserBrief] = []
    model_config = {"from_attributes": True}
