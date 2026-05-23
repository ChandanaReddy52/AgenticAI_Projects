"""
HireMind entry point.

Usage:
  # Start the API server
  python main.py

  # Run the pipeline directly from the CLI (for testing)
  python main.py --run-pipeline
"""

import argparse
import logging
import uvicorn
from config.settings import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def run_api():
    uvicorn.run(
        "api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


def run_pipeline_cli():
    """
    Minimal CLI runner — triggers the pipeline with a hardcoded sample job.
    Replace with your job data or wire to a YAML/JSON input file.
    """
    from graph.workflow import pipeline
    from graph.state import HireMindState
    import json

    sample_state: HireMindState = {
        "pipeline_stage": "JOB_POSTED",
        "next": "recruiter",
        "job_id": None,
        "job_title": "Senior Python Engineer",
        "job_description": (
            "We are looking for a Senior Python Engineer with strong experience in "
            "building distributed systems, REST APIs, and cloud-native architectures. "
            "The ideal candidate is proficient in Python, FastAPI, PostgreSQL, and AWS."
        ),
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "AWS"],
        "nice_to_have_skills": ["Docker", "Kubernetes", "LangChain"],
        "experience_years_min": 5,
        "location": "Remote",
        "remote_ok": True,
        "screening_results": [],
        "evaluation_results": [],
        "messages": [],
    }

    print("Starting HireMind pipeline...\n")
    final_state = pipeline.invoke(sample_state)

    print(f"\nPipeline complete. Stage: {final_state['pipeline_stage']}")
    print(f"Job ID: {final_state['job_id']}")
    print(f"\nScreening Results ({len(final_state['screening_results'])}):")
    for r in final_state["screening_results"]:
        print(f"  {r['name']} — {r['decision']} (score: {r['score']})")

    print(f"\nEvaluation Results ({len(final_state['evaluation_results'])}):")
    for r in final_state["evaluation_results"]:
        print(f"  {r['name']} — {r['recommendation']} (overall: {r['overall_score']:.1f})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HireMind MAS")
    parser.add_argument("--run-pipeline", action="store_true", help="Run pipeline via CLI instead of starting API")
    args = parser.parse_args()

    if args.run_pipeline:
        run_pipeline_cli()
    else:
        run_api()
