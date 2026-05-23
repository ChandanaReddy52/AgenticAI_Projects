"""
HireMind LangGraph workflow.

Pipeline stages:
  recruiter → screening → evaluation → END
                        ↘ END  (if no candidates shortlisted)
"""

from langgraph.graph import StateGraph, END
from graph.state import HireMindState
from agents.recruiter_agent import recruiter_node
from agents.screening_agent import screening_node
from agents.evaluation_agent import evaluation_node


def _route(state: HireMindState) -> str:
    """Read the routing signal written by each agent node."""
    return state.get("next", "end")


def build_workflow():
    graph = StateGraph(HireMindState)

    graph.add_node("recruiter", recruiter_node)
    graph.add_node("screening", screening_node)
    graph.add_node("evaluation", evaluation_node)

    graph.set_entry_point("recruiter")

    graph.add_conditional_edges(
        "recruiter",
        _route,
        {"screening": "screening", "end": END},
    )
    graph.add_conditional_edges(
        "screening",
        _route,
        {"evaluation": "evaluation", "end": END},
    )
    graph.add_conditional_edges(
        "evaluation",
        _route,
        {"end": END},
    )

    return graph.compile()


# Module-level compiled app — imported by api/app.py and main.py
pipeline = build_workflow()
