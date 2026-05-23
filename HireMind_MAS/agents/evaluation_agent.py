"""
Evaluation Agent — final assessment node.

Receives all shortlisted candidates from screening_results.
For each, uses LLM structured output to produce:
  technical_score (0–10), culture_fit_score (0–10),
  overall_score (0–10), recommendation (HIRE | NO_HIRE | HOLD), rationale.

Persists results to Supabase and sends hiring notifications.
"""

import logging
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage

from graph.state import HireMindState, EvaluationResult, ScreeningResult
from tools.candidate_tools import save_evaluation_result
from tools.communication_tools import notify_hired, notify_rejected
from config.settings import settings
import db.supabase_client as db

logger = logging.getLogger(__name__)


class _LLMEvaluationOutput(BaseModel):
    technical_score: float = Field(ge=0, le=10, description="Technical capability score 0–10")
    culture_fit_score: float = Field(ge=0, le=10, description="Culture fit score 0–10")
    overall_score: float = Field(ge=0, le=10, description="Overall score 0–10")
    recommendation: str = Field(description="One of: HIRE, NO_HIRE, HOLD")
    rationale: str = Field(description="Three-sentence hiring rationale")


_llm = ChatOpenAI(
    model=settings.openai_model,
    api_key=settings.openai_api_key,
    temperature=0,
)
_structured_llm = _llm.with_structured_output(_LLMEvaluationOutput)

_EVAL_PROMPT = """\
You are a senior hiring manager conducting a final candidate evaluation.

JOB TITLE: {job_title}

JOB DESCRIPTION:
{job_description}

CANDIDATE NAME: {name}

CANDIDATE RESUME:
{resume}

SCREENING SCORE: {screening_score}/100
SCREENING REASONING: {screening_reasoning}

Evaluate this candidate and provide:
- technical_score (0–10)
- culture_fit_score (0–10)
- overall_score (0–10)
- recommendation: HIRE (overall >= 7.0), HOLD (5.0–6.9), NO_HIRE (< 5.0)
- rationale (3 sentences)
"""


def evaluation_node(state: HireMindState) -> dict:
    shortlisted: list[ScreeningResult] = [
        r for r in state.get("screening_results", [])
        if r["decision"] == "SHORTLIST"
    ]

    if not shortlisted:
        logger.warning("EvaluationAgent: no shortlisted candidates to evaluate")
        return {
            "evaluation_results": [],
            "pipeline_stage": "DECISION",
            "next": "end",
            "messages": [AIMessage(content="No shortlisted candidates to evaluate.", name="EvaluationAgent")],
        }

    evaluation_results: list[EvaluationResult] = []

    for candidate in shortlisted:
        candidate_id = candidate["candidate_id"]
        name = candidate["name"]
        email = candidate["email"]

        # Retrieve application record to get application_id
        try:
            response = db.get_client().table("applications") \
                .select("id, resume:candidates(resume)") \
                .eq("job_id", state["job_id"]) \
                .eq("candidate_id", candidate_id) \
                .single().execute()
            application_id = response.data["id"]
            resume = response.data.get("resume", {}).get("resume", "")
        except Exception:
            logger.exception("EvaluationAgent: failed to fetch application for candidate %s", candidate_id)
            continue

        prompt = _EVAL_PROMPT.format(
            job_title=state["job_title"],
            job_description=state["job_description"],
            name=name,
            resume=resume,
            screening_score=candidate["score"],
            screening_reasoning=candidate["reasoning"],
        )

        try:
            output: _LLMEvaluationOutput = _structured_llm.invoke(prompt)
        except Exception:
            logger.exception("EvaluationAgent: LLM evaluation failed for candidate %s", candidate_id)
            continue

        # Enforce recommendation boundary
        if output.overall_score >= 7.0:
            recommendation = "HIRE"
        elif output.overall_score >= 5.0:
            recommendation = "HOLD"
        else:
            recommendation = "NO_HIRE"

        save_evaluation_result(
            application_id=application_id,
            technical_score=output.technical_score,
            culture_fit_score=output.culture_fit_score,
            overall_score=output.overall_score,
            recommendation=recommendation,
            rationale=output.rationale,
        )

        if recommendation == "HIRE":
            notify_hired(name, email, state["job_title"])
        elif recommendation == "NO_HIRE":
            notify_rejected(name, email, state["job_title"])
        # HOLD — no notification until decision is finalised

        db.log_agent_action(
            "evaluation", "evaluation_complete",
            job_id=state["job_id"], candidate_id=candidate_id,
            meta={"recommendation": recommendation, "overall_score": output.overall_score},
        )

        evaluation_results.append(EvaluationResult(
            candidate_id=candidate_id,
            name=name,
            email=email,
            technical_score=output.technical_score,
            culture_fit_score=output.culture_fit_score,
            overall_score=output.overall_score,
            recommendation=recommendation,
            rationale=output.rationale,
        ))
        logger.info("EvaluationAgent: %s → %s (%.1f)", name, recommendation, output.overall_score)

    summary = (
        f"Evaluated {len(evaluation_results)} candidates. "
        f"HIRE: {sum(1 for r in evaluation_results if r['recommendation'] == 'HIRE')}, "
        f"HOLD: {sum(1 for r in evaluation_results if r['recommendation'] == 'HOLD')}, "
        f"NO_HIRE: {sum(1 for r in evaluation_results if r['recommendation'] == 'NO_HIRE')}."
    )
    logger.info("EvaluationAgent: %s", summary)

    return {
        "evaluation_results": evaluation_results,
        "pipeline_stage": "DECISION",
        "next": "end",
        "messages": [AIMessage(content=summary, name="EvaluationAgent")],
    }
