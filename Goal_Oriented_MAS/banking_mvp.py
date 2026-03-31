# banking_mvp.py
import crewai
from crewai import Agent, Task, Crew, Process
import json
import re
import os

from validators import (
    validate_intent_output,
    validate_policy_output,
    decide_resolution
)

# -----------------------------
# AGENTS (roles + goals + constraints)
# -----------------------------
# Agent = LLM + persona + constraints
intent_classifier_agent = Agent(
    role="Intent Classification Agent",
    goal="Identify user intent, preliminary risk, and ambiguity",
    backstory="Specialist in understanding banking customer queries",
    verbose=True
)

policy_reasoning_agent = Agent(
    role="Policy Reasoning Agent",
    goal="Determine allowed and restricted actions based on banking rules",
    backstory="Expert in banking compliance and policy enforcement",
    verbose=True
)

response_drafting_agent = Agent(
    role="Response Drafting Agent",
    goal="Draft safe, policy-compliant responses for all resolution modes",
    backstory="Responsible for preparing user-facing language without making decisions",
    verbose=True
)


# -----------------------------
# TASKS (this is the logic flow)
# -----------------------------
# Task = prompt + expected output + assigned agent + context

intent_classification_task = Task(
    description="""
    You are an intent classification system for a BANKING SUPPORT PLATFORM.

    USER QUERY:
    "{user_query}"

    You MUST choose exactly ONE primary intent from this list:
    - transaction
    - loan
    - card
    - fraud
    - account_access
    - general

    STRICT DEFINITIONS:
    - transaction: money/ system/ payment issues without ownership denial
    - fraud : user claims lack of authorization OR lack of ownership OR lack of intent
    - card: physical card issues (lost, blocked, damaged, misuse)
    - loan: EMI, loan balance, repayment
    - account_access: login, password, access issues
    - general: non-financial queries

    NEGATIVE CONSTRAINTS:
    - A failed or pending transaction is NOT fraud by default
    - Do NOT classify fraud unless the user indicates non-authorization
    - Never invent new intent names
    """,

    expected_output="""
    Valid JSON with fields:
    primary_intent, secondary_intents, risk_level, confidence, ambiguity
    """,

    agent=intent_classifier_agent
)


policy_reasoning_task = Task(
    description="""
    Based on the classified intent provided above, determine:

    - allowed_actions (abstract verbs only, e.g. inform, guide_user)
    - restricted_actions
    - policy_notes

    Rules:
    - Do NOT include procedures
    - Do NOT include PII collection
    - Use abstract action names only
    """,

    expected_output="""
    Valid JSON with fields:
    allowed_actions, restricted_actions, policy_notes
    """,

    agent=policy_reasoning_agent,

    context=[intent_classification_task]  # IMP - Providing intent output as context to policy reasoning
)


response_drafting_task = Task(
    description="""
    You are given the classified intent and policy notes from previous agents.

    Based on this information, draft candidate responses for:
    - auto_resolve
    - guided_response
    - escalation_response

    Responses must respect policy constraints:
    - Never ask for sensitive PII
    - Never promise reversals or confirmations
    - Use neutral, safe language
    """,

    expected_output="""
    JSON with fields:
    auto_resolve_response, guided_response, escalation_response
    """,

    agent=response_drafting_agent
)

# -----------------------------
# CREW (the orchestrator)
# -----------------------------
# Crew = execution plan = Agents + Tasks + Process + Verbosity

banking_crew = Crew(
    agents=[
        intent_classifier_agent,
        policy_reasoning_agent,
        response_drafting_agent,
    ],
    tasks=[
        intent_classification_task,
        policy_reasoning_task,
        response_drafting_task,
    ],
    process=Process.sequential,
    verbose=True
)

# -----------------------------
# EXECUTION ENTRY POINT
# -----------------------------

# safe JSON extractor
def safe_json_load(raw_text: str) -> dict:
    """
    Extract JSON from LLM output that may include markdown fences.
    """
    if not raw_text:
        return {}

    # Remove markdown fences if present
    cleaned = re.sub(r"```json|```", "", raw_text).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {}
    
# -----------------------------
# TEST QUERIES
# -----------------------------
TEST_QUERIES = [
    {"query": "The amount got deducted but the payment failed.", "expected_primary": "transaction"},
    {"query": "I see a transaction I did not make.", "expected_primary": "fraud"},
    {"query": "Someone used my card without my permission.", "expected_primary": "fraud"},
    {"query": "My card is lost, please block it.", "expected_primary": "card"},
    {"query": "I want to know my loan EMI schedule.", "expected_primary": "loan"},
    {"query": "I cannot log into my account.", "expected_primary": "account_access"},
    {"query": "Payment is pending since yesterday.", "expected_primary": "transaction"},
    {"query": "Why is my balance not updated?", "expected_primary": "transaction"},
]

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    results = []

    for idx, item in enumerate(TEST_QUERIES, start=1):
        user_query = item["query"]

        banking_crew.kickoff(inputs={"user_query": user_query})

        # ---- Intent ----
        intent_dict = safe_json_load(intent_classification_task.output.raw)
        intent_validated = validate_intent_output(intent_dict, user_query)

        # ---- Policy ----
        policy_dict = safe_json_load(policy_reasoning_task.output.raw)
        policy_validated = validate_policy_output(policy_dict)

        # ---- Decision ----
        final_decision = decide_resolution(intent_validated, policy_validated)

        # >>> ADDED: extract drafted responses
        response_dict = safe_json_load(response_drafting_task.output.raw)

        # >>> ADDED: final response selection
        response_type = final_decision["selected_response_type"]
        final_response = response_dict.get(response_type)

        # >>> ADDED: full record for submission
        record = {
            "query": user_query,
            "expected_primary": item["expected_primary"],
            "llm_primary": intent_validated["_llm_primary_intent"],
            "system_primary": intent_validated["primary_intent"],
            "risk": intent_validated["risk_level"],
            "ambiguity": intent_validated["ambiguity"],
            "resolution_mode": final_decision["resolution_mode"],
            "selected_response_type": response_type,
            "final_response": final_response,
            "system_override": intent_validated["_system_override"]
        }

        results.append(record)
        print(json.dumps(record, indent=2))

    # >>> ADDED: persist final output for Phase-2 submission (deterministic path)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(current_dir, "output_results.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved Phase-2 results to: {output_path}")
