"""
HireMind FastAPI layer.

Endpoints:
  POST /pipeline/run     — trigger the full recruiter → screening → evaluation pipeline
  GET  /jobs/{job_id}    — retrieve job details from Supabase
  GET  /health           — liveness check
"""

import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from graph.workflow import pipeline
from graph.state import HireMindState
import db.supabase_client as db

logger = logging.getLogger(__name__)

app = FastAPI(title="HireMind MAS", version="1.0.0")


# ── Request / Response schemas ────────────────────────────────────────────────

class JobRequest(BaseModel):
    job_title: str
    job_description: str
    required_skills: list[str]
    nice_to_have_skills: list[str] = []
    experience_years_min: int = 0
    location: str = ""
    remote_ok: bool = False


class PipelineResponse(BaseModel):
    job_id: str
    pipeline_stage: str
    screening_results: list[dict]
    evaluation_results: list[dict]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/pipeline/run", response_model=PipelineResponse)
async def run_pipeline(request: JobRequest):
    """
    Trigger the full HireMind pipeline for a new job requisition.
    Runs recruiter → screening → evaluation and returns results.
    """
    initial_state: HireMindState = {
        "pipeline_stage": "JOB_POSTED",
        "next": "recruiter",
        "job_id": None,
        "job_title": request.job_title,
        "job_description": request.job_description,
        "required_skills": request.required_skills,
        "nice_to_have_skills": request.nice_to_have_skills,
        "experience_years_min": request.experience_years_min,
        "location": request.location,
        "remote_ok": request.remote_ok,
        "screening_results": [],
        "evaluation_results": [],
        "messages": [],
    }

    try:
        final_state = pipeline.invoke(initial_state)
    except Exception as exc:
        logger.exception("Pipeline execution failed")
        raise HTTPException(status_code=500, detail=str(exc))

    return PipelineResponse(
        job_id=final_state["job_id"],
        pipeline_stage=final_state["pipeline_stage"],
        screening_results=final_state.get("screening_results", []),
        evaluation_results=final_state.get("evaluation_results", []),
    )


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Return job details and all linked applications."""
    try:
        job = db.get_job(job_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")

    applications = (
        db.get_client()
        .table("applications")
        .select("*, candidates(name, email)")
        .eq("job_id", job_id)
        .execute()
        .data
    )
    return {"job": job, "applications": applications}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "hiremind-mas"}
