"""
Candidate Screening Agent — vector search + LLM scoring node.

Flow:
  1. Embed job_description → call match_candidates RPC → top 5 candidates.
  2. For each candidate, call LLM with structured output to produce:
       { candidate_id, name, email, score (0–100), decision, reasoning }
  3. Open an application record for every candidate evaluated.
  4. Persist screening results to each application record.
  5. Shortlisted candidates (score >= 70) advance to evaluation.
"""

import logging
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage

from graph.state import HireMindState, ScreeningResult
from memory import vector_store
from tools.candidate_tools import open_application, save_screening_result
from tools.communication_tools import notify_shortlisted, notify_rejected
from config.settings import settings
import db.supabase_client as db

logger = logging.getLogger(__name__)

SHORTLIST_THRESHOLD = 70


class _LLMScreeningOutput(BaseModel):
    score: int = Field(ge=0, le=100, description="Fit score from 0 to 100")
    decision: str = Field(description="SHORTLIST if score >= 70, else REJECT")
    reasoning: str = Field(description="Two-sentence explanation of the score")


_llm = ChatOpenAI(
    model=settings.openai_model,
    api_key=settings.openai_api_key,
    temperature=0,
)
_structured_llm = _llm.with_structured_output(_LLMScreeningOutput)

_SCORING_PROMPT = """\
You are an expert technical recruiter. Score the candidate's resume against the job description.

JOB DESCRIPTION:
{job_description}

CANDIDATE RESUME:
{resume}

Score the candidate from 0 to 100 on fit for this role.
Set decision to SHORTLIST if score >= 70, otherwise REJECT.
Provide concise reasoning (2 sentences max).
"""


def screening_node(state: HireMindState) -> dict:
    logger.info("ScreeningAgent: searching candidates for job '%s'", state["job_title"])

    candidates = vector_store.search_candidates(state["job_description"])

    if not candidates:
        logger.warning("ScreeningAgent: no candidates returned from vector search")
        msg = AIMessage(
            content="No candidates found in the database. Pipeline halted.",
            name="ScreeningAgent",
        )
        return {
            "screening_results": [],
            "pipeline_stage": "SCREENING_COMPLETE",
            "next": "end",
            "messages": [msg],
        }

    screening_results: list[ScreeningResult] = []

    for candidate in candidates:
        candidate_id = candidate["id"]
        name = candidate["name"]
        email = candidate["email"]
        resume = candidate["resume"]

        # LLM scoring
        prompt = _SCORING_PROMPT.format(
            job_description=state["job_description"],
            resume=resume,
        )
        try:
            output: _LLMScreeningOutput = _structured_llm.invoke(prompt)
        except Exception:
            logger.exception("LLM scoring failed for candidate %s — skipping", candidate_id)
            continue

        # Ensure decision aligns with score
        decision = "SHORTLIST" if output.score >= SHORTLIST_THRESHOLD else "REJECT"

        # Persist to Supabase
        application = open_application(state["job_id"], candidate_id)
        save_screening_result(
            application_id=application["id"],
            score=output.score,
            decision=decision,
            reasoning=output.reasoning,
        )

        # Notify candidate
        if decision == "SHORTLIST":
            notify_shortlisted(name, email, state["job_title"])
        else:
            notify_rejected(name, email, state["job_title"])

        db.log_agent_action(
            "screening", "candidate_scored",
            job_id=state["job_id"], candidate_id=candidate_id,
            meta={"score": output.score, "decision": decision},
        )

        screening_results.append(ScreeningResult(
            candidate_id=candidate_id,
            name=name,
            email=email,
            score=output.score,
            decision=decision,
            reasoning=output.reasoning,
        ))

    shortlisted = [r for r in screening_results if r["decision"] == "SHORTLIST"]
    next_node = "evaluation" if shortlisted else "end"

    summary = (
        f"Screened {len(screening_results)} candidates. "
        f"{len(shortlisted)} shortlisted for evaluation."
    )
    logger.info("ScreeningAgent: %s", summary)

    return {
        "screening_results": screening_results,
        "pipeline_stage": "SHORTLISTED" if shortlisted else "SCREENING_COMPLETE",
        "next": next_node,
        "messages": [AIMessage(content=summary, name="ScreeningAgent")],
    }
