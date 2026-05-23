from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class ScreeningResult(TypedDict):
    candidate_id: str
    name: str
    email: str
    score: int          # 0–100
    decision: str       # "SHORTLIST" | "REJECT"
    reasoning: str


class EvaluationResult(TypedDict):
    candidate_id: str
    name: str
    email: str
    technical_score: float      # 0–10
    culture_fit_score: float    # 0–10
    overall_score: float        # 0–10
    recommendation: str         # "HIRE" | "NO_HIRE" | "HOLD"
    rationale: str


class HireMindState(TypedDict):
    # Pipeline routing
    pipeline_stage: str     # JOB_POSTED | SCREENING | SHORTLISTED | EVALUATION | DECISION
    next: str               # node name or "end"

    # Job data (set at pipeline entry)
    job_id: str | None
    job_title: str
    job_description: str
    required_skills: list[str]
    nice_to_have_skills: list[str]
    experience_years_min: int
    location: str
    remote_ok: bool

    # Screening outputs (set by ScreeningAgent)
    screening_results: list[ScreeningResult]

    # Evaluation outputs (set by EvaluationAgent)
    evaluation_results: list[EvaluationResult]

    # Append-only message log for agent reasoning traces
    messages: Annotated[list, add_messages]
