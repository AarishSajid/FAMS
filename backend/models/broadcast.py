"""
Broadcast model — messages pushed to farmers.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SAEnum, func
from sqlalchemy.orm import relationship
from database import Base
from enums import BroadcastCategory


class Broadcast(Base):
    __tablename__ = "Broadcast"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    category = Column(SAEnum(BroadcastCategory, name="BroadcastCategory", create_type=True), nullable=True)
    districtId = Column(Integer, ForeignKey("District.id"), nullable=True)
    serviceCenterId = Column(Integer, ForeignKey("ServiceCenter.id"), nullable=True)
    createdById = Column(String, ForeignKey("User.id"), nullable=True)
    validFrom = Column(DateTime, server_default=func.now())
    validTo = Column(DateTime, nullable=True)
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────
    district = relationship("District", back_populates="broadcasts")
    createdBy = relationship("User", back_populates="createdBroadcasts")
