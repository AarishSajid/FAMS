"""
AdvisoryCase and all related workflow models:
  - AdvisoryVerification
  - AdvisoryFeedback
  - AdvisoryForwarding
  - AdvisoryClosure
  - AdvisoryEvent (audit trail)
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, ForeignKey, Text,
    Enum as SAEnum, func,
)
from sqlalchemy.orm import relationship
from database import Base
from enums import (
    AdvisoryCaseKind, IssueType, AdvisorySeverity,
    AdvisoryCaseState, VerificationOutcome,
)


class AdvisoryCase(Base):
    """Core FAMS workflow object — one trackable case per Agrobot advisory."""
    __tablename__ = "AdvisoryCase"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cycleId = Column(Integer, ForeignKey("Cycle.id"), nullable=False)
    farmId = Column(Integer, ForeignKey("Farm.id"), nullable=False)
    fieldCropId = Column(Integer, ForeignKey("FieldCrop.id"), nullable=True)
    sourceFarmAdvisoryId = Column(Integer, ForeignKey("FarmAdvisory.id"), nullable=True)
    serviceCenterId = Column(Integer, ForeignKey("ServiceCenter.id"), nullable=True)

    kind = Column(SAEnum(AdvisoryCaseKind, name="AdvisoryCaseKind", create_type=True), nullable=False)
    issueType = Column(SAEnum(IssueType, name="IssueType", create_type=True), nullable=True)
    severity = Column(SAEnum(AdvisorySeverity, name="AdvisorySeverity", create_type=True), nullable=True)
    state = Column(
        SAEnum(AdvisoryCaseState, name="AdvisoryCaseState", create_type=True),
        nullable=False,
        default=AdvisoryCaseState.RECEIVED,
    )
    text = Column(Text, nullable=True)
    assignedAgentId = Column(String, ForeignKey("User.id"), nullable=True)
    generatedAt = Column(DateTime, server_default=func.now())
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────
    cycle = relationship("Cycle", back_populates="cases")
    farm = relationship("Farm", back_populates="advisoryCases")
    fieldCrop = relationship("FieldCrop", back_populates="advisoryCases")
    sourceFarmAdvisory = relationship("FarmAdvisory", back_populates="generatedCases")
    serviceCenter = relationship("ServiceCenter", back_populates="advisoryCases")
    assignedAgent = relationship("User", back_populates="assignedAdvisoryCases", foreign_keys=[assignedAgentId])

    verification = relationship("AdvisoryVerification", back_populates="case", uselist=False)
    feedback = relationship("AdvisoryFeedback", back_populates="case", uselist=False)
    forwarding = relationship("AdvisoryForwarding", back_populates="case", uselist=False)
    closure = relationship("AdvisoryClosure", back_populates="case", uselist=False)
    events = relationship("AdvisoryEvent", back_populates="case", order_by="AdvisoryEvent.createdAt")


class AdvisoryVerification(Base):
    """Field agent's on-ground verification of an AdvisoryCase."""
    __tablename__ = "AdvisoryVerification"

    id = Column(Integer, primary_key=True, autoincrement=True)
    advisoryCaseId = Column(Integer, ForeignKey("AdvisoryCase.id"), nullable=False, unique=True)
    agentId = Column(String, ForeignKey("User.id"), nullable=False)
    outcome = Column(SAEnum(VerificationOutcome, name="VerificationOutcome", create_type=True), nullable=False)
    visitDate = Column(DateTime, nullable=True)
    observations = Column(Text, nullable=True)
    photos = Column(String, nullable=True)  # JSON array of URLs stored as string
    createdAt = Column(DateTime, server_default=func.now())

    # ── Relationships ─────────────────────────────────────────
    case = relationship("AdvisoryCase", back_populates="verification")
    agent = relationship("User", back_populates="verifications")


class AdvisoryFeedback(Base):
    """Mandatory feedback recorded for every case (BR-2)."""
    __tablename__ = "AdvisoryFeedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    advisoryCaseId = Column(Integer, ForeignKey("AdvisoryCase.id"), nullable=False, unique=True)
    recordedById = Column(String, ForeignKey("User.id"), nullable=False)
    outcome = Column(SAEnum(VerificationOutcome, name="VerificationOutcome", create_type=True), nullable=True)
    explanation = Column(Text, nullable=False)
    falsePositiveReason = Column(Text, nullable=True)
    returnedToAgrobot = Column(Boolean, default=True)
    returnedAt = Column(DateTime, nullable=True)
    createdAt = Column(DateTime, server_default=func.now())

    # ── Relationships ─────────────────────────────────────────
    case = relationship("AdvisoryCase", back_populates="feedback")
    recordedBy = relationship("User", back_populates="feedbackRecords")


class AdvisoryForwarding(Base):
    """Record of a case forwarded to the Farmer App (BR-1)."""
    __tablename__ = "AdvisoryForwarding"

    id = Column(Integer, primary_key=True, autoincrement=True)
    advisoryCaseId = Column(Integer, ForeignKey("AdvisoryCase.id"), nullable=False, unique=True)
    forwardedById = Column(String, ForeignKey("User.id"), nullable=False)
    forwardedAt = Column(DateTime, server_default=func.now())
    annotatedText = Column(Text, nullable=True)
    deliveredToFarmerApp = Column(Boolean, default=False)
    createdAt = Column(DateTime, server_default=func.now())

    # ── Relationships ─────────────────────────────────────────
    case = relationship("AdvisoryCase", back_populates="forwarding")
    forwardedBy = relationship("User", back_populates="forwardings")


class AdvisoryClosure(Base):
    """Record of a case closed without forwarding."""
    __tablename__ = "AdvisoryClosure"

    id = Column(Integer, primary_key=True, autoincrement=True)
    advisoryCaseId = Column(Integer, ForeignKey("AdvisoryCase.id"), nullable=False, unique=True)
    closedById = Column(String, ForeignKey("User.id"), nullable=False)
    reason = Column(Text, nullable=False)
    closedAt = Column(DateTime, server_default=func.now())
    createdAt = Column(DateTime, server_default=func.now())

    # ── Relationships ─────────────────────────────────────────
    case = relationship("AdvisoryCase", back_populates="closure")
    closedBy = relationship("User", back_populates="closures")


class AdvisoryEvent(Base):
    """Full audit trail — one row per state transition on a case (BR-5)."""
    __tablename__ = "AdvisoryEvent"

    id = Column(Integer, primary_key=True, autoincrement=True)
    advisoryCaseId = Column(Integer, ForeignKey("AdvisoryCase.id"), nullable=False)
    actorId = Column(String, ForeignKey("User.id"), nullable=True)
    label = Column(String, nullable=False)
    detail = Column(Text, nullable=True)
    stateSnapshot = Column(SAEnum(AdvisoryCaseState, name="AdvisoryCaseState", create_type=True), nullable=True)
    createdAt = Column(DateTime, server_default=func.now())

    # ── Relationships ─────────────────────────────────────────
    case = relationship("AdvisoryCase", back_populates="events")
    actor = relationship("User", back_populates="events")
