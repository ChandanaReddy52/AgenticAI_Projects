"""
Recruiter Agent — pipeline entry node.

Responsibilities:
  1. Create the job requisition in Supabase.
  2. Store job_id in pipeline state.
  3. Transition the pipeline to the SCREENING stage.
"""

import logging
from langchain_core.messages import AIMessage
from graph.state import HireMindState
from tools.job_tools import post_job

logger = logging.getLogger(__name__)


def recruiter_node(state: HireMindState) -> dict:
    logger.info("RecruiterAgent: posting job '%s'", state["job_title"])

    job = post_job(
        title=state["job_title"],
        description=state["job_description"],
        required_skills=state["required_skills"],
        nice_to_have_skills=state["nice_to_have_skills"],
        experience_years_min=state["experience_years_min"],
        location=state["location"],
        remote_ok=state["remote_ok"],
    )

    msg = AIMessage(
        content=f"Job '{job['title']}' created with ID {job['id']}. Transitioning to candidate screening.",
        name="RecruiterAgent",
    )

    return {
        "job_id": job["id"],
        "pipeline_stage": "SCREENING",
        "next": "screening",
        "messages": [msg],
    }
