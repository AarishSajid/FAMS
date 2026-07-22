"""
ServiceCenter and District models.
"""

from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class District(Base):
    __tablename__ = "District"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── FAMS back-relations ───────────────────────────────────
    serviceCenters = relationship("ServiceCenter", back_populates="district")
    weatherAlerts = relationship("WeatherAlert", back_populates="district")
    broadcasts = relationship("Broadcast", back_populates="district")


class ServiceCenter(Base):
    __tablename__ = "ServiceCenter"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    region = Column(String, nullable=True)
    districtId = Column(Integer, ForeignKey("District.id"), nullable=True)
    phone = Column(String, nullable=True)
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────
    district = relationship("District", back_populates="serviceCenters",
                            foreign_keys=[districtId],
                            primaryjoin="ServiceCenter.districtId == District.id")
    users = relationship("User", back_populates="serviceCenter")
    farms = relationship("Farm", back_populates="serviceCenter")
    advisoryCases = relationship("AdvisoryCase", back_populates="serviceCenter")
