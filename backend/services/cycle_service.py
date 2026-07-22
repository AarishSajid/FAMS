"""
Cycle generation logic — creates a new Cycle and ingests Agrobot output.
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func

from models.cycle import Cycle
from models.advisory import AdvisoryCase, AdvisoryEvent
from models.farm import Farm, FarmAdvisory
from enums import AdvisoryCaseState, AdvisoryCaseKind, IssueType, AdvisorySeverity
from services.rabbitmq_service import publish_advisory


def generate_cycle(db: Session) -> dict:
    """
    Open a new 5-day cycle and create AdvisoryCase rows from any completed
    Agrobot advisory that doesn't have a case yet.
    Returns summary dict with cycle info, cases created, and skipped farms.
    """
    now = datetime.now(timezone.utc)

    # Deactivate the previous active cycle
    db.query(Cycle).filter(Cycle.active == True).update({"active": False})

    # Determine the next cycle index
    last_cycle = db.query(Cycle).order_by(Cycle.index.desc()).first()
    next_index = (last_cycle.index + 1) if last_cycle else 1

    # Create new cycle
    cycle = Cycle(
        index=next_index,
        startDate=now,
        endDate=now + timedelta(days=5),
        active=True,
    )
    db.add(cycle)
    db.flush()  # get cycle.id

    # Find Agrobot advisories that don't have a case yet
    existing_source_ids = (
        db.query(AdvisoryCase.sourceFarmAdvisoryId)
        .filter(AdvisoryCase.sourceFarmAdvisoryId.isnot(None))
        .subquery()
    )

    unprocessed = (
        db.query(FarmAdvisory)
        .filter(
            FarmAdvisory.status == "COMPLETE",
            FarmAdvisory.id.notin_(existing_source_ids),
        )
        .all()
    )

    cases_created = 0
    skipped_no_service_center = []

    for advisory in unprocessed:
        # Look up the farm to get serviceCenterId
        farm = db.query(Farm).filter(Farm.id == advisory.farmId).first()
        if not farm:
            continue

        if not farm.serviceCenterId:
            skipped_no_service_center.append(farm.id)
            continue

        # Determine issue type and severity from advisory text (heuristic)
        issue_type = _classify_issue(advisory.advisoryText or "")
        severity = _classify_severity(advisory.advisoryText or "")

        payload = {
            "cycleId": cycle.id,
            "farmId": advisory.farmId,
            "fieldCropId": advisory.fieldCropId,
            "sourceFarmAdvisoryId": advisory.id,
            "serviceCenterId": farm.serviceCenterId,
            "kind": AdvisoryCaseKind.FARM_LEVEL.value,
            "issueType": issue_type.value,
            "severity": severity.value,
            "text": advisory.advisoryText,
            "detail": f"Cycle {next_index} · auto-generated from Agrobot advisory"
        }
        
        try:
            publish_advisory(payload)
            cases_created += 1
        except Exception as e:
            # Fallback or just log it
            import logging
            logging.getLogger("fams.cycle").error(f"Failed to publish to RabbitMQ: {e}")

    db.commit()
    db.refresh(cycle)

    return {
        "cycle": {
            "id": cycle.id,
            "index": cycle.index,
            "startDate": cycle.startDate.isoformat(),
            "endDate": cycle.endDate.isoformat(),
            "active": cycle.active,
        },
        "casesCreated": cases_created,
        "skippedNoServiceCenter": skipped_no_service_center,
    }


def _classify_issue(text: str) -> IssueType:
    """Simple keyword-based classification of advisory text."""
    text_lower = text.lower()
    if any(kw in text_lower for kw in ["pest", "jassid", "aphid", "insect", "infestation"]):
        return IssueType.PEST
    if any(kw in text_lower for kw in ["disease", "blight", "rust", "fungal"]):
        return IssueType.DISEASE
    if any(kw in text_lower for kw in ["nitrogen", "nutrient", "chlorophyll", "ndre"]):
        return IssueType.NUTRIENT
    if any(kw in text_lower for kw in ["water", "moisture", "irrigation", "ndmi", "stress"]):
        return IssueType.IRRIGATION
    if any(kw in text_lower for kw in ["weather", "heat", "rain", "frost"]):
        return IssueType.WEATHER
    return IssueType.OTHER


def _classify_severity(text: str) -> AdvisorySeverity:
    """Simple keyword-based severity classification."""
    text_lower = text.lower()
    if any(kw in text_lower for kw in ["critical", "severe", "urgent", "immediate"]):
        return AdvisorySeverity.CRITICAL
    if any(kw in text_lower for kw in ["high", "sharp drop", "significant"]):
        return AdvisorySeverity.HIGH
    if any(kw in text_lower for kw in ["moderate", "partial", "scattered"]):
        return AdvisorySeverity.MODERATE
    return AdvisorySeverity.LOW
