"""
Farm, FieldCrop, and FarmAdvisory models.
Farm and FieldCrop are existing Agriverse tables with additive FAMS columns.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from database import Base


class Farm(Base):
    __tablename__ = "Farm"

    id = Column(Integer, primary_key=True, autoincrement=True)
    farmer = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    village = Column(String, nullable=True)
    location = Column(String, nullable=True)
    acres = Column(Float, nullable=True)
    center = Column(String, nullable=True)  # Legacy string column — kept untouched
    boundary = Column(JSON, nullable=True)
    lon = Column(Float, nullable=True)
    lat = Column(Float, nullable=True)
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── FAMS additive columns ─────────────────────────────────
    serviceCenterId = Column(Integer, ForeignKey("ServiceCenter.id"), nullable=True)

    # ── Relationships ─────────────────────────────────────────
    serviceCenter = relationship("ServiceCenter", back_populates="farms")
    fieldCrops = relationship("FieldCrop", back_populates="farm")
    advisoryCases = relationship("AdvisoryCase", back_populates="farm")
    serviceRequests = relationship("ServiceRequest", back_populates="farm")
    productRequests = relationship("ProductRequest", back_populates="farm")


class FieldCrop(Base):
    __tablename__ = "FieldCrop"

    id = Column(Integer, primary_key=True, autoincrement=True)
    farmId = Column(Integer, ForeignKey("Farm.id"), nullable=False)
    crop = Column(String, nullable=True)
    variety = Column(String, nullable=True)
    sowDate = Column(DateTime, nullable=True)
    harvestDate = Column(DateTime, nullable=True)
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────
    farm = relationship("Farm", back_populates="fieldCrops")
    advisoryCases = relationship("AdvisoryCase", back_populates="fieldCrop")


class FarmAdvisory(Base):
    """Existing Agrobot-generated advisory (source data for AdvisoryCase)."""
    __tablename__ = "FarmAdvisory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    farmId = Column(Integer, ForeignKey("Farm.id"), nullable=True)
    fieldCropId = Column(Integer, ForeignKey("FieldCrop.id"), nullable=True)
    advisoryText = Column(String, nullable=True)
    status = Column(String, nullable=True)
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── FAMS back-relation ────────────────────────────────────
    generatedCases = relationship("AdvisoryCase", back_populates="sourceFarmAdvisory")
