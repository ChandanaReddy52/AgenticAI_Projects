"""Tools used by agents to manage candidate applications."""

import logging
import db.supabase_client as db

logger = logging.getLogger(__name__)


def open_application(job_id: str, candidate_id: str) -> dict:
    """Create an application record linking a candidate to a job."""
    application = db.create_application(job_id, candidate_id)
    db.log_agent_action(
        "screening", "application_created",
        job_id=job_id, candidate_id=candidate_id,
        meta={"application_id": application["id"]},
    )
    return application


def save_screening_result(
    application_id: str,
    score: float,
    decision: str,
    reasoning: str,
) -> None:
    """Persist screening scores and decision to the application record."""
    status = "SHORTLISTED" if decision == "SHORTLIST" else "REJECTED"
    db.update_application(application_id, {
        "status": status,
        "screening_score": score,
        "screening_decision": decision,
        "screening_reasoning": reasoning,
    })


def save_evaluation_result(
    application_id: str,
    technical_score: float,
    culture_fit_score: float,
    overall_score: float,
    recommendation: str,
    rationale: str,
) -> None:
    """Persist evaluation scores and hiring recommendation."""
    status_map = {"HIRE": "HIRED", "NO_HIRE": "REJECTED", "HOLD": "ON_HOLD"}
    db.update_application(application_id, {
        "status": status_map.get(recommendation, "ON_HOLD"),
        "technical_score": technical_score,
        "culture_fit_score": culture_fit_score,
        "overall_score": overall_score,
        "recommendation": recommendation,
        "evaluation_rationale": rationale,
    })
    db.log_agent_action(
        "evaluation", "evaluation_saved",
        meta={"application_id": application_id, "recommendation": recommendation},
    )
