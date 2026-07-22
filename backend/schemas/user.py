"""Pydantic schemas for user/field-agent endpoints."""

from pydantic import BaseModel


class AvailabilityRequest(BaseModel):
    availabilityStatus: str  # AVAILABLE, BUSY, OFF_DUTY


class FieldAgentListItem(BaseModel):
    id: str
    firstName: str | None = None
    lastName: str | None = None
    phone: str | None = None
    availabilityStatus: str | None = None
    serviceCenterId: int | None = None
    isActive: bool = True
    _count: dict | None = None
    model_config = {"from_attributes": True}


class LeaderboardEntry(BaseModel):
    agentId: str
    name: str
    casesAssigned: int = 0
    casesResolved: int = 0
    verificationsSubmitted: int = 0
    confirmedRate: float = 0.0
    avgTurnaroundHours: float = 0.0
