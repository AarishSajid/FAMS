"""
Advisory case state-machine enforcement (BR-1 through BR-6).
Keeps routers thin — all business logic lives here.
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from models.advisory import (
    AdvisoryCase, AdvisoryVerification, AdvisoryFeedback,
    AdvisoryForwarding, AdvisoryClosure, AdvisoryEvent,
)
from models.user import User
from enums import AdvisoryCaseState, VerificationOutcome
from exceptions import ConflictError, NotFoundError, BadRequestError
from redis_client import invalidate_leaderboard_center
from services.rabbitmq_service import publish_agrobot_feedback


def _write_event(
    db: Session,
    case: AdvisoryCase,
    label: str,
    actor: User | None,
    detail: str | None = None,
):
    """BR-5: every action writes an AdvisoryEvent row.
    stateSnapshot records the case state *after* this action's transition
    (i.e. the resulting state), captured before commit."""
    event = AdvisoryEvent(
        advisoryCaseId=case.id,
        actorId=actor.id if actor else None,
        label=label,
        detail=detail,
        stateSnapshot=case.state,
    )
    db.add(event)


def _get_case_or_404(db: Session, case_id: int) -> AdvisoryCase:
    # with_for_update serializes concurrent transitions on the same case so
    # two requests can't both pass their state guards (TOCTOU) and double-write.
    case = (
        db.query(AdvisoryCase)
        .filter(AdvisoryCase.id == case_id)
        .with_for_update()
        .first()
    )
    if not case:
        raise NotFoundError("AdvisoryCase", case_id)
    return case


# ── Actions ───────────────────────────────────────────────────

def assign_agent(db: Session, case_id: int, agent_id: str, actor: User) -> AdvisoryCase:
    """Assign a field agent to a case. Moves RECEIVED → UNDER_REVIEW."""
    case = _get_case_or_404(db, case_id)

    if case.state not in (AdvisoryCaseState.RECEIVED, AdvisoryCaseState.UNDER_REVIEW):
        raise ConflictError(
            f"Cannot assign agent: case is in state '{case.state.value}', "
            f"expected RECEIVED or UNDER_REVIEW."
        )

    agent = db.query(User).filter(User.id == agent_id).first()
    if not agent:
        raise NotFoundError("User (agent)", agent_id)

    case.assignedAgentId = agent_id
    if case.state == AdvisoryCaseState.RECEIVED:
        case.state = AdvisoryCaseState.UNDER_REVIEW

    _write_event(db, case, "ASSIGNED", actor,
                 detail=f"Assigned to {agent.firstName} {agent.lastName}")
    db.commit()
    db.refresh(case)
    return case


def submit_verification(
    db: Session,
    case_id: int,
    outcome: VerificationOutcome,
    visit_date: str | None,
    observations: str | None,
    photos: list[str] | None,
    actor: User,
) -> AdvisoryCase:
    """Field agent submits verification. Moves to VERIFIED_*. Once per case."""
    case = _get_case_or_404(db, case_id)

    if case.verification:
        raise ConflictError("Verification has already been submitted for this case.")

    if case.state not in (AdvisoryCaseState.UNDER_REVIEW, AdvisoryCaseState.PENDING_VERIFICATION):
        raise ConflictError(
            f"Cannot verify: case is in state '{case.state.value}', "
            f"expected UNDER_REVIEW or PENDING_VERIFICATION."
        )

    new_state = (
        AdvisoryCaseState.VERIFIED_CONFIRMED
        if outcome == VerificationOutcome.CONFIRMED
        else AdvisoryCaseState.VERIFIED_NOT_FOUND
    )
    case.state = new_state

    verification = AdvisoryVerification(
        advisoryCaseId=case_id,
        agentId=actor.id,
        outcome=outcome,
        visitDate=datetime.fromisoformat(visit_date) if visit_date else None,
        observations=observations,
        photos=",".join(photos) if photos else None,
    )
    db.add(verification)

    _write_event(db, case, "VERIFIED", actor,
                 detail=f"Verification outcome: {outcome.value}")
    db.commit()
    db.refresh(case)
    return case


def record_feedback(
    db: Session,
    case_id: int,
    explanation: str,
    false_positive_reason: str | None,
    actor: User,
) -> AdvisoryCase:
    """Record mandatory feedback (BR-2). Auto-returns to Agrobot (BR-6)."""
    case = _get_case_or_404(db, case_id)

    if case.feedback:
        raise ConflictError("Feedback has already been recorded for this case.")

    if case.state not in (
        AdvisoryCaseState.VERIFIED_CONFIRMED,
        AdvisoryCaseState.VERIFIED_NOT_FOUND,
    ):
        raise ConflictError(
            f"Cannot record feedback: case must be in a VERIFIED state, "
            f"got '{case.state.value}'."
        )

    now = datetime.now(timezone.utc)
    feedback_outcome = (
        case.verification.outcome if case.verification else None
    )

    feedback = AdvisoryFeedback(
        advisoryCaseId=case_id,
        recordedById=actor.id,
        outcome=feedback_outcome,
        explanation=explanation,
        falsePositiveReason=false_positive_reason,
        returnedToAgrobot=True,  # BR-6
        returnedAt=now,
    )
    db.add(feedback)

    case.state = AdvisoryCaseState.FEEDBACK_RECORDED

    _write_event(db, case, "FEEDBACK_RECORDED", actor)
    db.commit()
    db.refresh(case)

    # BR-6: actually return the feedback to Agrobot (not just flag it). Published
    # after commit so we never announce feedback that didn't persist.
    # ponytail: fire-and-forget publish; a transactional outbox is the upgrade if
    # guaranteed delivery is ever required.
    publish_agrobot_feedback({
        "caseId": case.id,
        "farmId": case.farmId,
        "sourceFarmAdvisoryId": case.sourceFarmAdvisoryId,
        "outcome": feedback_outcome.value if feedback_outcome else None,
        "explanation": explanation,
        "falsePositiveReason": false_positive_reason,
        "returnedAt": now.isoformat(),
    })
    return case


def forward_case(
    db: Session,
    case_id: int,
    annotated_text: str | None,
    actor: User,
) -> AdvisoryCase:
    """
    Forward to farmer (BR-1 + BR-4).
    MUST reject unless:
      - verification outcome is CONFIRMED
      - feedback exists (BR-2)
    """
    case = _get_case_or_404(db, case_id)

    # BR-4: closed cases can never be forwarded
    if case.state == AdvisoryCaseState.CLOSED_NOT_FORWARDED:
        raise ConflictError("This case has been closed and cannot be forwarded.")

    # BR-1: must be confirmed
    if not case.verification or case.verification.outcome != VerificationOutcome.CONFIRMED:
        raise ConflictError(
            "Cannot forward: case must have a CONFIRMED verification outcome (BR-1)."
        )

    # BR-2: feedback must exist
    if not case.feedback:
        raise ConflictError(
            "Cannot forward: mandatory feedback must be recorded first (BR-2)."
        )

    if case.state != AdvisoryCaseState.FEEDBACK_RECORDED:
        raise ConflictError(
            f"Cannot forward: case is in state '{case.state.value}', "
            f"expected FEEDBACK_RECORDED."
        )

    forwarding = AdvisoryForwarding(
        advisoryCaseId=case_id,
        forwardedById=actor.id,
        annotatedText=annotated_text,
        deliveredToFarmerApp=False,
    )
    db.add(forwarding)

    case.state = AdvisoryCaseState.FORWARDED

    _write_event(db, case, "FORWARDED", actor)
    db.commit()
    db.refresh(case)
    # Resolving a case changes agent standings — drop stale leaderboard windows.
    invalidate_leaderboard_center(case.serviceCenterId)
    return case


def close_case(
    db: Session,
    case_id: int,
    reason: str,
    actor: User,
) -> AdvisoryCase:
    """Close without forwarding. Requires feedback to already be recorded (BR-2)."""
    case = _get_case_or_404(db, case_id)

    if case.state == AdvisoryCaseState.FORWARDED:
        raise ConflictError("This case has already been forwarded and cannot be closed.")

    if case.state == AdvisoryCaseState.CLOSED_NOT_FORWARDED:
        raise ConflictError("This case is already closed.")

    # BR-2: feedback must exist
    if not case.feedback:
        raise ConflictError(
            "Cannot close: mandatory feedback must be recorded first (BR-2)."
        )

    if case.state != AdvisoryCaseState.FEEDBACK_RECORDED:
        raise ConflictError(
            f"Cannot close: case is in state '{case.state.value}', "
            f"expected FEEDBACK_RECORDED."
        )

    closure = AdvisoryClosure(
        advisoryCaseId=case_id,
        closedById=actor.id,
        reason=reason,
    )
    db.add(closure)

    case.state = AdvisoryCaseState.CLOSED_NOT_FORWARDED

    _write_event(db, case, "CLOSED", actor, detail=reason)
    db.commit()
    db.refresh(case)
    # Resolving a case changes agent standings — drop stale leaderboard windows.
    invalidate_leaderboard_center(case.serviceCenterId)
    return case
