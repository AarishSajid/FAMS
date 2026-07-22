"""
Python enums mirroring the 7 Prisma enums in the Agriverse database.
These are used in SQLAlchemy models and Pydantic schemas for type safety.
"""

import enum


class UserRole(str, enum.Enum):
    """Roles from the Agriverse User table."""
    ADMIN = "ADMIN"
    AGRONOMIST = "AGRONOMIST"
    FIELD_AGENT = "FIELD_AGENT"
    SERVICE_CENTER_MANAGER = "SERVICE_CENTER_MANAGER"
    CHIEF_AGRONOMIST = "CHIEF_AGRONOMIST"
    PROGRESSIVE_FARMER = "PROGRESSIVE_FARMER"


class FieldAgentAvailability(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    OFF_DUTY = "OFF_DUTY"


class AdvisoryCaseKind(str, enum.Enum):
    FARM_LEVEL = "FARM_LEVEL"
    WEATHER = "WEATHER"
    GENERAL = "GENERAL"


class IssueType(str, enum.Enum):
    PEST = "PEST"
    DISEASE = "DISEASE"
    NUTRIENT = "NUTRIENT"
    IRRIGATION = "IRRIGATION"
    WEATHER = "WEATHER"
    OTHER = "OTHER"


class AdvisorySeverity(str, enum.Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AdvisoryCaseState(str, enum.Enum):
    RECEIVED = "RECEIVED"
    UNDER_REVIEW = "UNDER_REVIEW"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    VERIFIED_CONFIRMED = "VERIFIED_CONFIRMED"
    VERIFIED_NOT_FOUND = "VERIFIED_NOT_FOUND"
    FEEDBACK_RECORDED = "FEEDBACK_RECORDED"
    FORWARDED = "FORWARDED"
    CLOSED_NOT_FORWARDED = "CLOSED_NOT_FORWARDED"


class VerificationOutcome(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    NOT_FOUND = "NOT_FOUND"


class BroadcastCategory(str, enum.Enum):
    ADVISORY = "ADVISORY"
    WEATHER = "WEATHER"
    SCHEME = "SCHEME"
    GENERAL = "GENERAL"


class ServiceRequestStatus(str, enum.Enum):
    """Service/product request lifecycle states."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
