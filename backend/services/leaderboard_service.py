"""
Leaderboard computation and Redis caching.
"""

import json
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func

from models.user import User
from models.advisory import AdvisoryCase, AdvisoryVerification
from enums import UserRole, AdvisoryCaseState, VerificationOutcome
from redis_client import get_cached_leaderboard, set_cached_leaderboard


def get_agent_leaderboard(
    db: Session,
    service_center_id: int | None = None,
    since_days: int = 30,
) -> list[dict]:
    """
    Compute per-agent performance metrics. Cached in Redis for 1 hour.
    """
    cache_key_id = service_center_id or 0

    # Check Redis cache first
    cached = get_cached_leaderboard(cache_key_id)
    if cached:
        return json.loads(cached)

    # Query field agents
    query = db.query(User).filter(User.role == UserRole.FIELD_AGENT)
    if service_center_id:
        query = query.filter(User.serviceCenterId == service_center_id)

    agents = query.all()
    results = []

    for agent in agents:
        assigned = (
            db.query(sql_func.count(AdvisoryCase.id))
            .filter(AdvisoryCase.assignedAgentId == agent.id)
            .scalar()
        )

        resolved = (
            db.query(sql_func.count(AdvisoryCase.id))
            .filter(
                AdvisoryCase.assignedAgentId == agent.id,
                AdvisoryCase.state.in_([
                    AdvisoryCaseState.FORWARDED,
                    AdvisoryCaseState.CLOSED_NOT_FORWARDED,
                ]),
            )
            .scalar()
        )

        verifications = (
            db.query(sql_func.count(AdvisoryVerification.id))
            .filter(AdvisoryVerification.agentId == agent.id)
            .scalar()
        )

        confirmed_count = (
            db.query(sql_func.count(AdvisoryVerification.id))
            .filter(
                AdvisoryVerification.agentId == agent.id,
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

    # Cache the result
    set_cached_leaderboard(cache_key_id, json.dumps(results))

    return results
