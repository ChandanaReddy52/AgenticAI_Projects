"""Tools used by the Recruiter Agent to manage job requisitions."""

import logging
import db.supabase_client as db

logger = logging.getLogger(__name__)


def post_job(
    title: str,
    description: str,
    required_skills: list[str],
    nice_to_have_skills: list[str],
    experience_years_min: int,
    location: str,
    remote_ok: bool,
) -> dict:
    """Insert a new job into Supabase and return the created record."""
    payload = {
        "title": title,
        "description": description,
        "required_skills": required_skills,
        "nice_to_have_skills": nice_to_have_skills,
        "experience_years_min": experience_years_min,
        "location": location,
        "remote_ok": remote_ok,
        "status": "OPEN",
    }
    job = db.create_job(payload)
    db.log_agent_action("recruiter", "job_posted", job_id=job["id"], meta={"title": title})
    logger.info("Job posted: %s (%s)", title, job["id"])
    return job


def close_job(job_id: str) -> None:
    db.update_job_status(job_id, "CLOSED")
    db.log_agent_action("recruiter", "job_closed", job_id=job_id)
