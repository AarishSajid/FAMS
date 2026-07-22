"""
User model — reflects the existing Agriverse User table
with the additive FAMS columns (serviceCenterId, availabilityStatus).
"""

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from database import Base
from enums import UserRole, FieldAgentAvailability


class User(Base):
    __tablename__ = "User"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=True)
    password = Column(String, nullable=False)
    firstName = Column(String, nullable=True)
    lastName = Column(String, nullable=True)
    role = Column(SAEnum(UserRole, name="UserRole", create_type=True), nullable=False)
    isActive = Column(Boolean, default=True)
    lastLogin = Column(DateTime, nullable=True)
    createdAt = Column(DateTime, nullable=False)
    updatedAt = Column(DateTime, nullable=False)

    # ── FAMS additive columns ─────────────────────────────────
    serviceCenterId = Column(Integer, ForeignKey("ServiceCenter.id"), nullable=True)
    availabilityStatus = Column(
        SAEnum(FieldAgentAvailability, name="FieldAgentAvailability", create_type=True),
        nullable=True,
    )

    # ── Relationships ─────────────────────────────────────────
    serviceCenter = relationship("ServiceCenter", back_populates="users")
    assignedAdvisoryCases = relationship("AdvisoryCase", back_populates="assignedAgent", foreign_keys="AdvisoryCase.assignedAgentId")
    verifications = relationship("AdvisoryVerification", back_populates="agent")
    feedbackRecords = relationship("AdvisoryFeedback", back_populates="recordedBy")
    forwardings = relationship("AdvisoryForwarding", back_populates="forwardedBy")
    closures = relationship("AdvisoryClosure", back_populates="closedBy")
    events = relationship("AdvisoryEvent", back_populates="actor")
    handledServiceRequests = relationship("ServiceRequest", back_populates="handledBy", foreign_keys="ServiceRequest.handledById")
    createdBroadcasts = relationship("Broadcast", back_populates="createdBy")
