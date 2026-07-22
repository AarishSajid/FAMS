"""
WeatherAlert model — district-scoped severity-tagged alerts.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SAEnum, func
from sqlalchemy.orm import relationship
from database import Base
from enums import AdvisorySeverity


class WeatherAlert(Base):
    __tablename__ = "WeatherAlert"

    id = Column(Integer, primary_key=True, autoincrement=True)
    districtId = Column(Integer, ForeignKey("District.id"), nullable=False)
    alertType = Column(String, nullable=False)
    severity = Column(SAEnum(AdvisorySeverity, name="AdvisorySeverity", create_type=True), nullable=False)
    headline = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    validFrom = Column(DateTime, nullable=False)
    validTo = Column(DateTime, nullable=True)
    source = Column(String, default="manual")
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────
    district = relationship("District", back_populates="weatherAlerts")
