"""
Leaderboard computation and Redis caching.
"""

import json
import time
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func

from models.user import User
from models.advisory import AdvisoryCase, AdvisoryVerification
from enums import UserRole, AdvisoryCaseState, VerificationOutcome
from redis_client import (
    get_cached_leaderboard,
    set_cached_leaderboard,
    acquire_lock,
    release_lock,
)


def get_agent_leaderboard(
    db: Session,
    service_center_id: int | None = None,
    since_days: int = 30,
) -> list[dict]:
    """
    Compute per-agent performance metrics over the last `since_days`, cached in
    Redis for ~1 hour. A single-flight lock guards against cache stampede: on a
    miss only one caller recomputes; the rest briefly wait for its result.
    """
    # Window is part of the key so a 7-day request can't serve a 30-day payload.
    cache_key = f"{service_center_id or 0}:{since_days}"

    cached = get_cached_leaderboard(cache_key)
    if cached:
        return json.loads(cached)

    have_lock = acquire_lock(f"leaderboard:{cache_key}")
    if not have_lock:
        # Someone else is already recomputing — wait up to ~1s for their write.
        for _ in range(20):
            time.sleep(0.05)
            cached = get_cached_leaderboard(cache_key)
            if cached:
                return json.loads(cached)
        # Winner still hasn't published; fall through and compute ourselves.

    try:
        results = _compute_leaderboard(db, service_center_id, since_days)
        set_cached_leaderboard(cache_key, json.dumps(results))
        return results
    finally:
        if have_lock:
            release_lock(f"leaderboard:{cache_key}")


def _compute_leaderboard(
    db: Session,
    service_center_id: int | None,
    since_days: int,
) -> list[dict]:
    cutoff = datetime.utcnow() - timedelta(days=since_days)

    query = db.query(User).filter(User.role == UserRole.FIELD_AGENT)
    if service_center_id:
        query = query.filter(User.serviceCenterId == service_center_id)

    agents = query.all()
    results = []

    for agent in agents:
        assigned = (
            db.query(sql_func.count(AdvisoryCase.id))
            .filter(
                AdvisoryCase.assignedAgentId == agent.id,
                AdvisoryCase.generatedAt >= cutoff,
            )
            .scalar()
        )

        resolved = (
            db.query(sql_func.count(AdvisoryCase.id))
            .filter(
                AdvisoryCase.assignedAgentId == agent.id,
                AdvisoryCase.generatedAt >= cutoff,
                AdvisoryCase.state.in_([
                    AdvisoryCaseState.FORWARDED,
                    AdvisoryCaseState.CLOSED_NOT_FORWARDED,
                ]),
            )
            .scalar()
        )

        verifications = (
            db.query(sql_func.count(AdvisoryVerification.id))
            .filter(
                AdvisoryVerification.agentId == agent.id,
                AdvisoryVerification.createdAt >= cutoff,
            )
            .scalar()
        )

        confirmed_count = (
            db.query(sql_func.count(AdvisoryVerification.id))
            .filter(
                AdvisoryVerification.agentId == agent.id,
                AdvisoryVerification.createdAt >= cutoff,
                AdvisoryVerification.outcome == VerificationOutcome.CONFIRMED,
            )
            .scalar()
        )

        confirmed_rate = (confirmed_count / verifications) if verifications > 0 else 0.0

        results.append({
            "agentId": agent.id,
            "name": f"{agent.firstName or ''} {agent.lastName or ''}".strip(),
            "casesAssigned": assigned,
            "casesResolved": resolved,
            "verificationsSubmitted": verifications,
            "confirmedRate": round(confirmed_rate, 2),
            "avgTurnaroundHours": 0,  # TODO: compute from event timestamps
        })

    # Sort by resolved count descending
    results.sort(key=lambda x: x["casesResolved"], reverse=True)
    return results
