"""Pydantic schemas for advisory case workflow endpoints."""

from pydantic import BaseModel
from datetime import datetime


# ── Request schemas ───────────────────────────────────────────

class AssignAgentRequest(BaseModel):
    agentId: str


class VerificationRequest(BaseModel):
    outcome: str  # "CONFIRMED" or "NOT_FOUND"
    visitDate: str | None = None
    observations: str | None = None
    photos: list[str] | None = None


class FeedbackRequest(BaseModel):
    explanation: str
    falsePositiveReason: str | None = None


class ForwardRequest(BaseModel):
    annotatedText: str | None = None


class CloseRequest(BaseModel):
    reason: str


# ── Response schemas ──────────────────────────────────────────

class FarmBrief(BaseModel):
    id: int
    farmer: str | None = None
    phone: str | None = None
    village: str | None = None
    model_config = {"from_attributes": True}


class AgentBrief(BaseModel):
    id: str
    firstName: str | None = None
    lastName: str | None = None
    phone: str | None = None
    availabilityStatus: str | None = None
    model_config = {"from_attributes": True}


class CycleBrief(BaseModel):
    id: int
    index: int
    model_config = {"from_attributes": True}


class ServiceCenterBrief(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class VerificationResponse(BaseModel):
    outcome: str
    visitDate: datetime | None = None
    observations: str | None = None
    model_config = {"from_attributes": True}


class FeedbackResponse(BaseModel):
    outcome: str | None = None
    explanation: str
    returnedToAgrobot: bool = True
    returnedAt: datetime | None = None
    model_config = {"from_attributes": True}


class ForwardingResponse(BaseModel):
    id: int
    advisoryCaseId: int
    forwardedById: str
    forwardedAt: datetime | None = None
    deliveredToFarmerApp: bool = False
    model_config = {"from_attributes": True}


class ClosureResponse(BaseModel):
    id: int
    advisoryCaseId: int
    reason: str
    closedById: str
    closedAt: datetime | None = None
    model_config = {"from_attributes": True}


class EventResponse(BaseModel):
    id: int
    advisoryCaseId: int
    label: str
    actorLabel: str | None = None
    detail: str | None = None
    at: datetime | None = None
    stateSnapshot: str | None = None
    model_config = {"from_attributes": True}


class AdvisoryCaseListItem(BaseModel):
    id: int
    farmId: int
    fieldCropId: int | None = None
    cycleId: int
    serviceCenterId: int | None = None
    kind: str
    issueType: str | None = None
    severity: str | None = None
    text: str | None = None
    state: str
    assignedAgentId: str | None = None
    generatedAt: datetime | None = None
    farm: FarmBrief | None = None
    assignedAgent: AgentBrief | None = None
    cycle: CycleBrief | None = None
    verification: VerificationResponse | None = None
    feedback: FeedbackResponse | None = None
    model_config = {"from_attributes": True}


class AdvisoryCaseDetail(BaseModel):
    id: int
    farmId: int
    fieldCropId: int | None = None
    cycleId: int
    serviceCenterId: int | None = None
    kind: str
    issueType: str | None = None
    severity: str | None = None
    text: str | None = None
    state: str
    farm: FarmBrief | None = None
    serviceCenter: ServiceCenterBrief | None = None
    assignedAgent: AgentBrief | None = None
    verification: VerificationResponse | None = None
    feedback: FeedbackResponse | None = None
    forwarding: ForwardingResponse | None = None
    closure: ClosureResponse | None = None
    events: list[EventResponse] = []
    model_config = {"from_attributes": True}
