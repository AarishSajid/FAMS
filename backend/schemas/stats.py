"""Pydantic schemas for dashboard stats endpoints."""

from pydantic import BaseModel
from datetime import datetime


class KPIResponse(BaseModel):
    serviceCenterId: int
    activeCycle: dict | None = None
    openCases: int = 0
    overdueVerifications: int = 0
    pendingRequests: int = 0
    closedThisCycle: int = 0


class TrendItem(BaseModel):
    cycleId: int
    cycleIndex: int
    startDate: str
    totalCases: int = 0
    forwarded: int = 0
    closedNotForwarded: int = 0
    verificationAccuracy: float = 0.0


class MapFarmItem(BaseModel):
    id: int
    farmer: str | None = None
    village: str | None = None
    location: str | None = None
    lat: float | None = None
    lon: float | None = None
    openCaseCount: int = 0
    highestSeverity: str | None = None
    cases: list[dict] = []
