"""
Advisory Case router — full state machine workflow.
9 endpoints covering the entire Agrobot → verify → forward/close lifecycle.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.advisory import AdvisoryCase, AdvisoryEvent
from models.user import User
from schemas.advisory import (
    AssignAgentRequest, VerificationRequest, FeedbackRequest,
    ForwardRequest, CloseRequest, AdvisoryCaseListItem, EventResponse,
)
from services import advisory_service, cycle_service
from dependencies import authorize
from enums import UserRole, AdvisoryCaseState, VerificationOutcome
from exceptions import NotFoundError

router = APIRouter(prefix="/advisory-case", tags=["Advisory Cases"])


# ── Cycle generation ──────────────────────────────────────────

@router.post("/cycles/generate")
def generate_cycle(
    db: Session = Depends(get_db),
    user: User = Depends(authorize(UserRole.ADMIN, UserRole.CHIEF_AGRONOMIST, UserRole.SERVICE_CENTER_MANAGER)),
):
    """Create a new 5-day cycle and ingest unprocessed Agrobot advisories."""
    result = cycle_service.generate_cycle(db)
    return result


# ── List / Detail ─────────────────────────────────────────────

@router.get("/")
def list_advisory_cases(
    serviceCenterId: int | None = Query(None),
    cycleId: int | None = Query(None),
    state: str | None = Query(None),
    kind: str | None = Query(None),
    severity: str | None = Query(None),
    assignedAgentId: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(authorize(
        UserRole.ADMIN, UserRole.SERVICE_CENTER_MANAGER, UserRole.CHIEF_AGRONOMIST, UserRole.FIELD_AGENT,
    )),
):
    """List advisory cases with optional filters."""
    query = db.query(AdvisoryCase).options(
        joinedload(AdvisoryCase.farm),
        joinedload(AdvisoryCase.assignedAgent),
        joinedload(AdvisoryCase.cycle),
        joinedload(AdvisoryCase.verification),
        joinedload(AdvisoryCase.feedback),
    )

    if serviceCenterId is not None:
        query = query.filter(AdvisoryCase.serviceCenterId == serviceCenterId)
    if cycleId is not None:
        query = query.filter(AdvisoryCase.cycleId == cycleId)
    if state:
        query = query.filter(AdvisoryCase.state == state)
    if kind:
        query = query.filter(AdvisoryCase.kind == kind)
    if severity:
        query = query.filter(AdvisoryCase.severity == severity)
    if assignedAgentId:
        query = query.filter(AdvisoryCase.assignedAgentId == assignedAgentId)

    total = query.count()
    cases = query.order_by(AdvisoryCase.generatedAt.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": [_case_to_list_item(c) for c in cases],
    }


@router.get("/{case_id}")
def get_advisory_case(
    case_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(authorize(
        UserRole.ADMIN, UserRole.SERVICE_CENTER_MANAGER, UserRole.CHIEF_AGRONOMIST, UserRole.FIELD_AGENT,
    )),
):
    """Get full case detail including all workflow sub-records and event timeline."""
    case = (
        db.query(AdvisoryCase)
        .options(
            joinedload(AdvisoryCase.farm),
            joinedload(AdvisoryCase.assignedAgent),
            joinedload(AdvisoryCase.cycle),
            joinedload(AdvisoryCase.serviceCenter),
            joinedload(AdvisoryCase.verification),
            joinedload(AdvisoryCase.feedback),
            joinedload(AdvisoryCase.forwarding),
            joinedload(AdvisoryCase.closure),
            joinedload(AdvisoryCase.events),
        )
        .filter(AdvisoryCase.id == case_id)
        .first()
    )
    if not case:
        raise NotFoundError("AdvisoryCase", case_id)

    return _case_to_detail(case)


# ── Workflow actions ──────────────────────────────────────────

@router.patch("/{case_id}/assign")
def assign_agent(
    case_id: int,
    body: AssignAgentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(authorize(UserRole.SERVICE_CENTER_MANAGER, UserRole.ADMIN)),
):
    case = advisory_service.assign_agent(db, case_id, body.agentId, user)
    return {"message": "Agent assigned", "caseId": case.id, "state": case.state.value}


@router.post("/{case_id}/verification")
def submit_verification(
    case_id: int,
    body: VerificationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(authorize(UserRole.FIELD_AGENT, UserRole.SERVICE_CENTER_MANAGER, UserRole.ADMIN)),
):
    outcome = VerificationOutcome(body.outcome)
    case = advisory_service.submit_verification(
        db, case_id, outcome, body.visitDate, body.observations, body.photos, user,
    )
    return {"message": "Verification submitted", "caseId": case.id, "state": case.state.value}


@router.post("/{case_id}/feedback")
def record_feedback(
    case_id: int,
    body: FeedbackRequest,
    db: Session = Depends(get_db),
    user: User = Depends(authorize(UserRole.SERVICE_CENTER_MANAGER, UserRole.ADMIN)),
):
    case = advisory_service.record_feedback(
        db, case_id, body.explanation, body.falsePositiveReason, user,
    )
    return {"message": "Feedback recorded (BR-6: returned to Agrobot)", "caseId": case.id, "state": case.state.value}


@router.post("/{case_id}/forward")
def forward_case(
    case_id: int,
    body: ForwardRequest,
    db: Session = Depends(get_db),
    user: User = Depends(authorize(UserRole.SERVICE_CENTER_MANAGER, UserRole.ADMIN)),
):
    """Forward to farmer. Enforces BR-1, BR-2, BR-4."""
    case = advisory_service.forward_case(db, case_id, body.annotatedText, user)
    return {"message": "Case forwarded to farmer", "caseId": case.id, "state": case.state.value}


@router.post("/{case_id}/close")
def close_case(
    case_id: int,
    body: CloseRequest,
    db: Session = Depends(get_db),
    user: User = Depends(authorize(UserRole.SERVICE_CENTER_MANAGER, UserRole.ADMIN)),
):
    """Close without forwarding. Enforces BR-2."""
    case = advisory_service.close_case(db, case_id, body.reason, user)
    return {"message": "Case closed (not forwarded)", "caseId": case.id, "state": case.state.value}


@router.get("/{case_id}/events")
def get_case_events(
    case_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(authorize(
        UserRole.ADMIN, UserRole.SERVICE_CENTER_MANAGER, UserRole.CHIEF_AGRONOMIST, UserRole.FIELD_AGENT,
    )),
):
    """Get the full audit timeline for a case (BR-5)."""
    events = (
        db.query(AdvisoryEvent)
        .filter(AdvisoryEvent.advisoryCaseId == case_id)
        .order_by(AdvisoryEvent.createdAt.asc())
        .all()
    )
    return [
        {
            "id": e.id,
            "advisoryCaseId": e.advisoryCaseId,
            "label": e.label,
            "actorId": e.actorId,
            "detail": e.detail,
            "at": e.createdAt.isoformat() if e.createdAt else None,
            "stateSnapshot": e.stateSnapshot.value if e.stateSnapshot else None,
        }
        for e in events
    ]


# ── Helpers ───────────────────────────────────────────────────

def _case_to_list_item(c: AdvisoryCase) -> dict:
    return {
        "id": c.id,
        "farmId": c.farmId,
        "cycleId": c.cycleId,
        "kind": c.kind.value if c.kind else None,
        "issueType": c.issueType.value if c.issueType else None,
        "severity": c.severity.value if c.severity else None,
        "state": c.state.value if c.state else None,
        "text": c.text,
        "assignedAgentId": c.assignedAgentId,
        "generatedAt": c.generatedAt.isoformat() if c.generatedAt else None,
        "farm": {"id": c.farm.id, "farmer": c.farm.farmer, "village": c.farm.village} if c.farm else None,
        "assignedAgent": {
            "id": c.assignedAgent.id,
            "firstName": c.assignedAgent.firstName,
            "lastName": c.assignedAgent.lastName,
        } if c.assignedAgent else None,
        "cycle": {"id": c.cycle.id, "index": c.cycle.index} if c.cycle else None,
        "verification": {
            "outcome": c.verification.outcome.value if c.verification.outcome else None,
            "observations": c.verification.observations,
        } if c.verification else None,
        "feedback": {
            "explanation": c.feedback.explanation,
            "returnedToAgrobot": c.feedback.returnedToAgrobot,
        } if c.feedback else None,
    }


def _case_to_detail(c: AdvisoryCase) -> dict:
    detail = _case_to_list_item(c)
    detail["serviceCenter"] = {"id": c.serviceCenter.id, "name": c.serviceCenter.name} if c.serviceCenter else None
    detail["forwarding"] = {
        "id": c.forwarding.id,
        "forwardedById": c.forwarding.forwardedById,
        "forwardedAt": c.forwarding.forwardedAt.isoformat() if c.forwarding.forwardedAt else None,
        "deliveredToFarmerApp": c.forwarding.deliveredToFarmerApp,
    } if c.forwarding else None
    detail["closure"] = {
        "id": c.closure.id,
        "reason": c.closure.reason,
        "closedById": c.closure.closedById,
        "closedAt": c.closure.closedAt.isoformat() if c.closure.closedAt else None,
    } if c.closure else None
    detail["events"] = [
        {
            "id": e.id,
            "label": e.label,
            "actorId": e.actorId,
            "detail": e.detail,
            "at": e.createdAt.isoformat() if e.createdAt else None,
            "stateSnapshot": e.stateSnapshot.value if e.stateSnapshot else None,
        }
        for e in (c.events or [])
    ]
    return detail
