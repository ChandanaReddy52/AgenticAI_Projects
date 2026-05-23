"""
Supabase client — single shared instance for all DB operations.

Tables:
  candidates   — pre-populated externally (name, email, resume, embedding)
  jobs         — job requisitions created by Recruiter Agent
  applications — job ↔ candidate link with scores and status
  interviews   — scheduled interview records
  agent_logs   — agent action audit trail
"""

import logging
from supabase import create_client, Client
from config.settings import settings

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _client


# ── Jobs ─────────────────────────────────────────────────────────────────────

def create_job(payload: dict) -> dict:
    response = get_client().table("jobs").insert(payload).execute()
    return response.data[0]


def get_job(job_id: str) -> dict:
    response = get_client().table("jobs").select("*").eq("id", job_id).single().execute()
    return response.data


def update_job_status(job_id: str, status: str) -> None:
    get_client().table("jobs").update({"status": status}).eq("id", job_id).execute()


# ── Applications ──────────────────────────────────────────────────────────────

def create_application(job_id: str, candidate_id: str) -> dict:
    response = get_client().table("applications").insert({
        "job_id": job_id,
        "candidate_id": candidate_id,
        "status": "APPLIED",
    }).execute()
    return response.data[0]


def update_application(application_id: str, payload: dict) -> None:
    get_client().table("applications").update(payload).eq("id", application_id).execute()


def get_application(application_id: str) -> dict:
    response = get_client().table("applications").select("*").eq("id", application_id).single().execute()
    return response.data


# ── Interviews ────────────────────────────────────────────────────────────────

def create_interview(application_id: str, scheduled_at: str, meeting_link: str) -> dict:
    response = get_client().table("interviews").insert({
        "application_id": application_id,
        "scheduled_at": scheduled_at,
        "meeting_link": meeting_link,
    }).execute()
    return response.data[0]


# ── Agent audit log ───────────────────────────────────────────────────────────

def log_agent_action(
    agent: str,
    action: str,
    job_id: str | None = None,
    candidate_id: str | None = None,
    meta: dict | None = None,
) -> None:
    try:
        get_client().table("agent_logs").insert({
            "agent": agent,
            "action": action,
            "job_id": job_id,
            "candidate_id": candidate_id,
            "meta": meta or {},
        }).execute()
    except Exception:
        logger.exception("Failed to write agent log (non-fatal)")
