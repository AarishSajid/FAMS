"""
Cycle model — a recurring 5-day advisory window.
"""

from sqlalchemy import Column, Integer, DateTime, Boolean, func
from sqlalchemy.orm import relationship
from database import Base


class Cycle(Base):
    __tablename__ = "Cycle"

    id = Column(Integer, primary_key=True, autoincrement=True)
    index = Column(Integer, nullable=False, unique=True)
    startDate = Column(DateTime, nullable=False)
    endDate = Column(DateTime, nullable=False)
    active = Column(Boolean, default=True)
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────
    cases = relationship("AdvisoryCase", back_populates="cycle")
