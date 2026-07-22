"""
Dashboard stats aggregation — KPIs, trends, and map data.
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func

from models.advisory import AdvisoryCase
from models.cycle import Cycle
from models.farm import Farm
from models.service_request import ServiceRequest
from enums import AdvisoryCaseState, ServiceRequestStatus


def get_kpis(db: Session, service_center_id: int) -> dict:
    """KPI tiles for the manager morning dashboard."""
    # Active cycle. NOTE: cycles are global (system-wide), not per-center, so this
    # assumes a single active cycle across all service centers.
    active_cycle = db.query(Cycle).filter(Cycle.active == True).first()

    # Open cases (not in a terminal state)
    terminal_states = [AdvisoryCaseState.FORWARDED, AdvisoryCaseState.CLOSED_NOT_FORWARDED]
    open_cases = (
        db.query(sql_func.count(AdvisoryCase.id))
        .filter(
            AdvisoryCase.serviceCenterId == service_center_id,
            AdvisoryCase.state.notin_(terminal_states),
        )
        .scalar()
    )

    # Overdue verifications (assigned but no verification in 2+ days)
    two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)
    overdue = (
        db.query(sql_func.count(AdvisoryCase.id))
        .filter(
            AdvisoryCase.serviceCenterId == service_center_id,
            AdvisoryCase.state.in_([
                AdvisoryCaseState.UNDER_REVIEW,
                AdvisoryCaseState.PENDING_VERIFICATION,
            ]),
            AdvisoryCase.updatedAt < two_days_ago,
        )
        .scalar()
    )

    # Pending service requests
    pending_requests = (
        db.query(sql_func.count(ServiceRequest.id))
        .filter(
            ServiceRequest.serviceCenterId == service_center_id,
            ServiceRequest.status == ServiceRequestStatus.PENDING,
        )
        .scalar()
    )

    # Closed this cycle
    closed_this_cycle = 0
    if active_cycle:
        closed_this_cycle = (
            db.query(sql_func.count(AdvisoryCase.id))
            .filter(
                AdvisoryCase.serviceCenterId == service_center_id,
                AdvisoryCase.cycleId == active_cycle.id,
                AdvisoryCase.state.in_(terminal_states),
            )
            .scalar()
        )

    return {
        "serviceCenterId": service_center_id,
        "activeCycle": {
            "id": active_cycle.id if active_cycle else None,
            "index": active_cycle.index if active_cycle else None,
            "endDate": active_cycle.endDate.isoformat() if active_cycle else None,
        } if active_cycle else None,
        "openCases": open_cases,
        "overdueVerifications": overdue,
        "pendingRequests": pending_requests,
        "closedThisCycle": closed_this_cycle,
    }


def get_trends(db: Session, service_center_id: int, num_cycles: int = 10) -> list[dict]:
    """Trend data: cases per cycle and verification accuracy over the last N cycles."""
    cycles = (
        db.query(Cycle)
        .order_by(Cycle.index.desc())
        .limit(num_cycles)
        .all()
    )
    cycles.reverse()  # oldest first

    results = []
    for cycle in cycles:
        total = (
            db.query(sql_func.count(AdvisoryCase.id))
            .filter(
                AdvisoryCase.serviceCenterId == service_center_id,
                AdvisoryCase.cycleId == cycle.id,
            )
            .scalar()
        )

        forwarded = (
            db.query(sql_func.count(AdvisoryCase.id))
            .filter(
                AdvisoryCase.serviceCenterId == service_center_id,
                AdvisoryCase.cycleId == cycle.id,
                AdvisoryCase.state == AdvisoryCaseState.FORWARDED,
            )
            .scalar()
        )

        closed = (
            db.query(sql_func.count(AdvisoryCase.id))
            .filter(
                AdvisoryCase.serviceCenterId == service_center_id,
                AdvisoryCase.cycleId == cycle.id,
                AdvisoryCase.state == AdvisoryCaseState.CLOSED_NOT_FORWARDED,
            )
            .scalar()
        )

        accuracy = (forwarded / total) if total > 0 else 0.0

        results.append({
            "cycleId": cycle.id,
            "cycleIndex": cycle.index,
            "startDate": cycle.startDate.isoformat() if cycle.startDate else None,
            "totalCases": total,
            "forwarded": forwarded,
            "closedNotForwarded": closed,
            "verificationAccuracy": round(accuracy, 2),
        })

    return results


def get_map_data(db: Session, service_center_id: int) -> list[dict]:
    """Farm map data with open case counts and severity for colour-coding markers."""
    farms = db.query(Farm).filter(Farm.serviceCenterId == service_center_id).all()
    terminal_states = [AdvisoryCaseState.FORWARDED, AdvisoryCaseState.CLOSED_NOT_FORWARDED]

    results = []
    for farm in farms:
        open_cases = [c for c in farm.advisoryCases if c.state not in terminal_states]

        # Determine highest severity among open cases
        severity_order = {"CRITICAL": 4, "HIGH": 3, "MODERATE": 2, "LOW": 1}
        highest_severity = None
        if open_cases:
            highest_severity = max(
                open_cases,
                key=lambda c: severity_order.get(c.severity.value if c.severity else "LOW", 0),
            ).severity

        results.append({
            "id": farm.id,
            "farmer": farm.farmer,
            "village": farm.village,
            "location": farm.location,
            "lat": farm.lat,
            "lon": farm.lon,
            "openCaseCount": len(open_cases),
            "highestSeverity": highest_severity.value if highest_severity else None,
            "cases": [
                {
                    "id": c.id,
                    "state": c.state.value,
                    "severity": c.severity.value if c.severity else None,
                    "kind": c.kind.value,
                }
                for c in open_cases
            ],
        })

    return results
