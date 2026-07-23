"""
Initial migration — baseline schema for all FAMS tables.

This migration creates every table that was previously built by
Base.metadata.create_all(). Going forward, all schema changes are
managed through Alembic revision scripts instead.

Revision ID: 0001
Revises: (none — this is the first migration)
Create Date: 2026-07-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum types (create_type=False on columns to avoid double-creation) ──
    # We create them explicitly first, then reference them in tables.
    bind = op.get_bind()

    user_role = postgresql.ENUM(
        "ADMIN", "AGRONOMIST", "FIELD_AGENT", "SERVICE_CENTER_MANAGER",
        "CHIEF_AGRONOMIST", "PROGRESSIVE_FARMER",
        name="UserRole", create_type=False,
    )
    field_agent_availability = postgresql.ENUM(
        "AVAILABLE", "BUSY", "OFF_DUTY",
        name="FieldAgentAvailability", create_type=False,
    )
    advisory_case_kind = postgresql.ENUM(
        "FARM_LEVEL", "WEATHER", "GENERAL",
        name="AdvisoryCaseKind", create_type=False,
    )
    issue_type = postgresql.ENUM(
        "PEST", "DISEASE", "NUTRIENT", "IRRIGATION", "WEATHER", "OTHER",
        name="IssueType", create_type=False,
    )
    advisory_severity = postgresql.ENUM(
        "LOW", "MODERATE", "HIGH", "CRITICAL",
        name="AdvisorySeverity", create_type=False,
    )
    advisory_case_state = postgresql.ENUM(
        "RECEIVED", "UNDER_REVIEW", "PENDING_VERIFICATION",
        "VERIFIED_CONFIRMED", "VERIFIED_NOT_FOUND",
        "FEEDBACK_RECORDED", "FORWARDED", "CLOSED_NOT_FORWARDED",
        name="AdvisoryCaseState", create_type=False,
    )
    verification_outcome = postgresql.ENUM(
        "CONFIRMED", "NOT_FOUND",
        name="VerificationOutcome", create_type=False,
    )
    broadcast_category = postgresql.ENUM(
        "ADVISORY", "WEATHER", "SCHEME", "GENERAL",
        name="BroadcastCategory", create_type=False,
    )
    service_request_status = postgresql.ENUM(
        "PENDING", "IN_PROGRESS", "COMPLETED", "REJECTED",
        name="ServiceRequestStatus", create_type=False,
    )

    # Create all enum types in Postgres (checkfirst avoids errors on re-run)
    user_role.create(bind, checkfirst=True)
    field_agent_availability.create(bind, checkfirst=True)
    advisory_case_kind.create(bind, checkfirst=True)
    issue_type.create(bind, checkfirst=True)
    advisory_severity.create(bind, checkfirst=True)
    advisory_case_state.create(bind, checkfirst=True)
    verification_outcome.create(bind, checkfirst=True)
    broadcast_category.create(bind, checkfirst=True)
    service_request_status.create(bind, checkfirst=True)

    # ── District ──────────────────────────────────────────────
    op.create_table(
        "District",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # ── ServiceCenter ─────────────────────────────────────────
    op.create_table(
        "ServiceCenter",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("districtId", sa.Integer(), sa.ForeignKey("District.id"), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── User ──────────────────────────────────────────────────
    op.create_table(
        "User",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("password", sa.String(), nullable=False),
        sa.Column("firstName", sa.String(), nullable=True),
        sa.Column("lastName", sa.String(), nullable=True),
        sa.Column("role", user_role, nullable=False),
        sa.Column("isActive", sa.Boolean(), default=True),
        sa.Column("lastLogin", sa.DateTime(), nullable=True),
        sa.Column("createdAt", sa.DateTime(), nullable=False),
        sa.Column("updatedAt", sa.DateTime(), nullable=False),
        sa.Column("serviceCenterId", sa.Integer(), sa.ForeignKey("ServiceCenter.id"), nullable=True),
        sa.Column("availabilityStatus", field_agent_availability, nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )

    # ── Farm ──────────────────────────────────────────────────
    op.create_table(
        "Farm",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("farmer", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("village", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("acres", sa.Float(), nullable=True),
        sa.Column("center", sa.String(), nullable=True),
        sa.Column("boundary", sa.JSON(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("serviceCenterId", sa.Integer(), sa.ForeignKey("ServiceCenter.id"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── FieldCrop ─────────────────────────────────────────────
    op.create_table(
        "FieldCrop",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("farmId", sa.Integer(), sa.ForeignKey("Farm.id"), nullable=False),
        sa.Column("crop", sa.String(), nullable=True),
        sa.Column("variety", sa.String(), nullable=True),
        sa.Column("sowDate", sa.DateTime(), nullable=True),
        sa.Column("harvestDate", sa.DateTime(), nullable=True),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── FarmAdvisory ──────────────────────────────────────────
    op.create_table(
        "FarmAdvisory",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("farmId", sa.Integer(), sa.ForeignKey("Farm.id"), nullable=True),
        sa.Column("fieldCropId", sa.Integer(), sa.ForeignKey("FieldCrop.id"), nullable=True),
        sa.Column("advisoryText", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Cycle ─────────────────────────────────────────────────
    op.create_table(
        "Cycle",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column("startDate", sa.DateTime(), nullable=False),
        sa.Column("endDate", sa.DateTime(), nullable=False),
        sa.Column("active", sa.Boolean(), default=True),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("index"),
    )

    # ── AdvisoryCase ──────────────────────────────────────────
    op.create_table(
        "AdvisoryCase",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cycleId", sa.Integer(), sa.ForeignKey("Cycle.id"), nullable=False),
        sa.Column("farmId", sa.Integer(), sa.ForeignKey("Farm.id"), nullable=False),
        sa.Column("fieldCropId", sa.Integer(), sa.ForeignKey("FieldCrop.id"), nullable=True),
        sa.Column("sourceFarmAdvisoryId", sa.Integer(), sa.ForeignKey("FarmAdvisory.id"), nullable=True),
        sa.Column("serviceCenterId", sa.Integer(), sa.ForeignKey("ServiceCenter.id"), nullable=True),
        sa.Column("kind", advisory_case_kind, nullable=False),
        sa.Column("issueType", issue_type, nullable=True),
        sa.Column("severity", advisory_severity, nullable=True),
        sa.Column("state", advisory_case_state, nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("assignedAgentId", sa.String(), sa.ForeignKey("User.id"), nullable=True),
        sa.Column("generatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── AdvisoryVerification ──────────────────────────────────
    op.create_table(
        "AdvisoryVerification",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("advisoryCaseId", sa.Integer(), sa.ForeignKey("AdvisoryCase.id"), nullable=False),
        sa.Column("agentId", sa.String(), sa.ForeignKey("User.id"), nullable=False),
        sa.Column("outcome", verification_outcome, nullable=False),
        sa.Column("visitDate", sa.DateTime(), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("photos", sa.String(), nullable=True),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("advisoryCaseId"),
    )

    # ── AdvisoryFeedback ──────────────────────────────────────
    op.create_table(
        "AdvisoryFeedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("advisoryCaseId", sa.Integer(), sa.ForeignKey("AdvisoryCase.id"), nullable=False),
        sa.Column("recordedById", sa.String(), sa.ForeignKey("User.id"), nullable=False),
        sa.Column("outcome", verification_outcome, nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("falsePositiveReason", sa.Text(), nullable=True),
        sa.Column("returnedToAgrobot", sa.Boolean(), default=True),
        sa.Column("returnedAt", sa.DateTime(), nullable=True),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("advisoryCaseId"),
    )

    # ── AdvisoryForwarding ────────────────────────────────────
    op.create_table(
        "AdvisoryForwarding",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("advisoryCaseId", sa.Integer(), sa.ForeignKey("AdvisoryCase.id"), nullable=False),
        sa.Column("forwardedById", sa.String(), sa.ForeignKey("User.id"), nullable=False),
        sa.Column("forwardedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("annotatedText", sa.Text(), nullable=True),
        sa.Column("deliveredToFarmerApp", sa.Boolean(), default=False),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("advisoryCaseId"),
    )

    # ── AdvisoryClosure ───────────────────────────────────────
    op.create_table(
        "AdvisoryClosure",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("advisoryCaseId", sa.Integer(), sa.ForeignKey("AdvisoryCase.id"), nullable=False),
        sa.Column("closedById", sa.String(), sa.ForeignKey("User.id"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("closedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("advisoryCaseId"),
    )

    # ── AdvisoryEvent ─────────────────────────────────────────
    op.create_table(
        "AdvisoryEvent",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("advisoryCaseId", sa.Integer(), sa.ForeignKey("AdvisoryCase.id"), nullable=False),
        sa.Column("actorId", sa.String(), sa.ForeignKey("User.id"), nullable=True),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("stateSnapshot", advisory_case_state, nullable=True),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Service ───────────────────────────────────────────────
    op.create_table(
        "Service",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rate", sa.Float(), nullable=True),
        sa.Column("isActive", sa.Boolean(), default=True),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── ServiceRequest ────────────────────────────────────────
    op.create_table(
        "ServiceRequest",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("farmId", sa.Integer(), sa.ForeignKey("Farm.id"), nullable=False),
        sa.Column("serviceId", sa.Integer(), sa.ForeignKey("Service.id"), nullable=False),
        sa.Column("status", service_request_status, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("requestedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("serviceCenterId", sa.Integer(), sa.ForeignKey("ServiceCenter.id"), nullable=True),
        sa.Column("basePrice", sa.Float(), nullable=True),
        sa.Column("petrolCost", sa.Float(), nullable=True),
        sa.Column("totalCost", sa.Float(), nullable=True),
        sa.Column("scheduledFor", sa.DateTime(), nullable=True),
        sa.Column("completedAt", sa.DateTime(), nullable=True),
        sa.Column("declineReason", sa.Text(), nullable=True),
        sa.Column("handledById", sa.String(), sa.ForeignKey("User.id"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Product ───────────────────────────────────────────────
    op.create_table(
        "Product",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rate", sa.Float(), nullable=True),
        sa.Column("isActive", sa.Boolean(), default=True),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── ProductRequest ────────────────────────────────────────
    op.create_table(
        "ProductRequest",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("farmId", sa.Integer(), sa.ForeignKey("Farm.id"), nullable=False),
        sa.Column("productId", sa.Integer(), sa.ForeignKey("Product.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), default=1),
        sa.Column("status", service_request_status, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("requestedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Broadcast ─────────────────────────────────────────────
    op.create_table(
        "Broadcast",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("category", broadcast_category, nullable=True),
        sa.Column("districtId", sa.Integer(), sa.ForeignKey("District.id"), nullable=True),
        sa.Column("serviceCenterId", sa.Integer(), sa.ForeignKey("ServiceCenter.id"), nullable=True),
        sa.Column("createdById", sa.String(), sa.ForeignKey("User.id"), nullable=True),
        sa.Column("validFrom", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("validTo", sa.DateTime(), nullable=True),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── WeatherAlert ──────────────────────────────────────────
    op.create_table(
        "WeatherAlert",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("districtId", sa.Integer(), sa.ForeignKey("District.id"), nullable=False),
        sa.Column("alertType", sa.String(), nullable=False),
        sa.Column("severity", advisory_severity, nullable=False),
        sa.Column("headline", sa.String(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("validFrom", sa.DateTime(), nullable=False),
        sa.Column("validTo", sa.DateTime(), nullable=True),
        sa.Column("source", sa.String(), default="manual"),
        sa.Column("createdAt", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updatedAt", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table("WeatherAlert")
    op.drop_table("Broadcast")
    op.drop_table("ProductRequest")
    op.drop_table("Product")
    op.drop_table("ServiceRequest")
    op.drop_table("Service")
    op.drop_table("AdvisoryEvent")
    op.drop_table("AdvisoryClosure")
    op.drop_table("AdvisoryForwarding")
    op.drop_table("AdvisoryFeedback")
    op.drop_table("AdvisoryVerification")
    op.drop_table("AdvisoryCase")
    op.drop_table("Cycle")
    op.drop_table("FarmAdvisory")
    op.drop_table("FieldCrop")
    op.drop_table("Farm")
    op.drop_table("User")
    op.drop_table("ServiceCenter")
    op.drop_table("District")

    # Drop enum types
    bind = op.get_bind()
    for name in [
        "ServiceRequestStatus", "BroadcastCategory", "VerificationOutcome",
        "AdvisoryCaseState", "AdvisorySeverity", "IssueType",
        "AdvisoryCaseKind", "FieldAgentAvailability", "UserRole",
    ]:
        postgresql.ENUM(name=name).drop(bind, checkfirst=True)
