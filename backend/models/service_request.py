"""
Service, ServiceRequest, Product, and ProductRequest models.
Service/Product are existing catalogue tables.
ServiceRequest has FAMS additive columns for pricing and scheduling.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text,
    Enum as SAEnum, func,
)
from sqlalchemy.orm import relationship
from database import Base
from enums import ServiceRequestStatus


class Service(Base):
    """Service catalogue (existing Agriverse table)."""
    __tablename__ = "Service"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    rate = Column(Float, nullable=True)
    isActive = Column(Boolean, default=True)
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────
    requests = relationship("ServiceRequest", back_populates="service")


class ServiceRequest(Base):
    """Service request with FAMS additive columns for manager workflow."""
    __tablename__ = "ServiceRequest"

    id = Column(Integer, primary_key=True, autoincrement=True)
    farmId = Column(Integer, ForeignKey("Farm.id"), nullable=False)
    serviceId = Column(Integer, ForeignKey("Service.id"), nullable=False)
    status = Column(
        SAEnum(ServiceRequestStatus, name="ServiceRequestStatus", create_type=True),
        nullable=False,
        default=ServiceRequestStatus.PENDING,
    )
    notes = Column(Text, nullable=True)
    requestedAt = Column(DateTime, server_default=func.now())
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── FAMS additive columns ─────────────────────────────────
    serviceCenterId = Column(Integer, ForeignKey("ServiceCenter.id"), nullable=True)
    basePrice = Column(Float, nullable=True)
    petrolCost = Column(Float, nullable=True)
    totalCost = Column(Float, nullable=True)
    scheduledFor = Column(DateTime, nullable=True)
    completedAt = Column(DateTime, nullable=True)
    declineReason = Column(Text, nullable=True)
    handledById = Column(String, ForeignKey("User.id"), nullable=True)

    # ── Relationships ─────────────────────────────────────────
    farm = relationship("Farm", back_populates="serviceRequests")
    service = relationship("Service", back_populates="requests")
    handledBy = relationship("User", back_populates="handledServiceRequests", foreign_keys=[handledById])


class Product(Base):
    """Product catalogue (existing Agriverse table)."""
    __tablename__ = "Product"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    rate = Column(Float, nullable=True)
    isActive = Column(Boolean, default=True)
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────
    requests = relationship("ProductRequest", back_populates="product")


class ProductRequest(Base):
    """Product request from a farmer — goods order, not a field visit."""
    __tablename__ = "ProductRequest"

    id = Column(Integer, primary_key=True, autoincrement=True)
    farmId = Column(Integer, ForeignKey("Farm.id"), nullable=False)
    productId = Column(Integer, ForeignKey("Product.id"), nullable=False)
    quantity = Column(Integer, default=1)
    status = Column(
        SAEnum(ServiceRequestStatus, name="ServiceRequestStatus", create_type=True),
        nullable=False,
        default=ServiceRequestStatus.PENDING,
    )
    notes = Column(Text, nullable=True)
    requestedAt = Column(DateTime, server_default=func.now())
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────
    farm = relationship("Farm", back_populates="productRequests")
    product = relationship("Product", back_populates="requests")
