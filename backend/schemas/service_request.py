"""Pydantic schemas for service and product request endpoints."""

from pydantic import BaseModel
from datetime import datetime


# ── Service Request schemas ───────────────────────────────────

class ServiceResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    rate: float | None = None
    isActive: bool = True
    model_config = {"from_attributes": True}


class CreateServiceRequest(BaseModel):
    farmId: int
    notes: str | None = None


class CostRequest(BaseModel):
    petrolCost: float


class ScheduleRequest(BaseModel):
    scheduledFor: str
    handledById: str | None = None


class DeclineRequest(BaseModel):
    declineReason: str


class FarmBrief(BaseModel):
    id: int
    farmer: str | None = None
    phone: str | None = None
    village: str | None = None
    model_config = {"from_attributes": True}


class ServiceRequestResponse(BaseModel):
    id: int
    farmId: int
    serviceId: int | None = None
    status: str
    notes: str | None = None
    requestedAt: datetime | None = None
    basePrice: float | None = None
    petrolCost: float | None = None
    totalCost: float | None = None
    scheduledFor: datetime | None = None
    completedAt: datetime | None = None
    declineReason: str | None = None
    service: ServiceResponse | None = None
    farm: FarmBrief | None = None
    model_config = {"from_attributes": True}


# ── Product Request schemas ───────────────────────────────────

class ProductResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    rate: float | None = None
    isActive: bool = True
    model_config = {"from_attributes": True}


class CreateProductRequest(BaseModel):
    farmId: int
    quantity: int = 1
    notes: str | None = None


class ProductRequestResponse(BaseModel):
    id: int
    farmId: int
    productId: int | None = None
    quantity: int = 1
    status: str
    notes: str | None = None
    requestedAt: datetime | None = None
    product: ProductResponse | None = None
    farm: FarmBrief | None = None
    model_config = {"from_attributes": True}
