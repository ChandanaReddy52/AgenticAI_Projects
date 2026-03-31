from typing import Dict, Any, Tuple, Optional

# -----------------------------
# FIXED TAXONOMIES (NON-NEGOTIABLE)
# -----------------------------

PRIMARY_INTENTS = {
    "transaction",
    "loan",
    "card",
    "fraud",
    "account_access",
    "general"
}

RISK_LEVELS = {"low", "medium", "high"}

# System minimum risk per intent (business truth)
SYSTEM_MIN_RISK = {
    "fraud": "high",
    "transaction": "medium",
    "card": "medium",
    "loan": "low",
    "account_access": "medium",
    "general": "low"
}

RISK_ORDER = ["low", "medium", "high"]

# -----------------------------
# HELPERS
# -----------------------------

def max_risk(a: str, b: str) -> str:
    return RISK_ORDER[max(RISK_ORDER.index(a), RISK_ORDER.index(b))]


def enforce_fraud_definition(
    llm_intent: str,
    user_query: str
) -> Tuple[str, Optional[str]]:
    """
    Fraud is ONLY valid if the user indicates:
    - lack of authorization
    - lack of ownership
    - lack of intent
    """

    fraud_markers = [
        "did not make",
        "was not me",
        "unauthorized",
        "unknown transaction",
        "someone else",
        "without my permission"
    ]

    q = user_query.lower()
    has_fraud_claim = any(marker in q for marker in fraud_markers)

    if llm_intent == "fraud" and not has_fraud_claim:
        return "transaction", "fraud_downgraded_no_authorization_claim"

    return llm_intent, None


# -----------------------------
# INTENT VALIDATION (SYSTEM AUTHORITY)
# -----------------------------

def validate_intent_output(output: Dict[str, Any], user_query: str) -> Dict[str, Any]:
    validated = {}

    # 1️⃣ Capture raw LLM proposal (observability)
    llm_primary = output.get("primary_intent", "general")
    llm_risk = output.get("risk_level", "medium")
    llm_ambiguity = output.get("ambiguity", True)

    validated["_llm_primary_intent"] = llm_primary
    validated["_llm_risk_level"] = llm_risk
    validated["_llm_ambiguity"] = llm_ambiguity

    # 2️⃣ Normalize confidence FIRST (used later)
    try:
        confidence = float(output.get("confidence", 0.5))
    except Exception:
        confidence = 0.5
    confidence = max(0.0, min(confidence, 1.0))
    validated["confidence"] = confidence

    # 3️⃣ Normalize intent & risk
    primary_intent = llm_primary if llm_primary in PRIMARY_INTENTS else "general"

    risk = llm_risk.lower() if isinstance(llm_risk, str) else "medium"
    risk = risk if risk in RISK_LEVELS else "medium"

    # 4️⃣ Normalize ambiguity (LLM → system boolean)
    if isinstance(llm_ambiguity, bool):
        ambiguity = llm_ambiguity
    elif isinstance(llm_ambiguity, str):
        ambiguity = llm_ambiguity.lower() in {"medium", "high"}
    else:
        ambiguity = True

    # 5️⃣ Enforce fraud eligibility (can CHANGE intent)
    primary_intent, system_override = enforce_fraud_definition(
        primary_intent,
        user_query
    )

    # 6️⃣ Risk = max(system minimum, LLM proposed)
    risk = max_risk(
        SYSTEM_MIN_RISK[primary_intent],
        risk
    )

    # 7️⃣ Final ambiguity reconciliation
    if (
        validated["_llm_primary_intent"] == primary_intent
        and confidence >= 0.8
    ):
        ambiguity = False

    # 8️⃣ Final validated output
    validated["primary_intent"] = primary_intent
    validated["risk_level"] = risk
    validated["ambiguity"] = ambiguity
    validated["_system_override"] = system_override

    # Secondary intents (pass-through only)
    secondary = output.get("secondary_intents", [])
    validated["secondary_intents"] = secondary if isinstance(secondary, list) else []

    return validated


# -----------------------------
# POLICY VALIDATION
# -----------------------------

def validate_policy_output(output: Dict[str, Any]) -> Dict[str, Any]:
    if not output:
        return {
            "allowed_actions": [],
            "restricted_actions": ["unknown_policy_state"],
            "policy_notes": "Policy reasoning failed; defaulting to safe constraints"
        }

    return {
        "allowed_actions": output.get("allowed_actions", []),
        "restricted_actions": output.get("restricted_actions", []),
        "policy_notes": str(output.get("policy_notes", ""))
    }


# -----------------------------
# ESCALATION RULES (FINAL AUTHORITY)
# -----------------------------

NON_AUTOMATABLE_INTENTS = {"transaction", "fraud", "card"}
CONFIDENCE_THRESHOLD = 0.6


def decide_resolution(intent: dict, policy: dict) -> dict:
    primary_intent = intent["primary_intent"]
    risk_level = intent["risk_level"]
    ambiguity = intent["ambiguity"]
    confidence = intent["confidence"]
    restricted_actions = policy["restricted_actions"]

    if primary_intent == "fraud":
        return _escalate(
            "Fraud-related issues require human verification",
            ["fraud_intent"]
        )

    if primary_intent in NON_AUTOMATABLE_INTENTS and risk_level == "high":
        return _escalate(
            "High-risk sensitive intent cannot be automated",
            ["high_risk_sensitive_intent"]
        )

    if ambiguity and primary_intent in NON_AUTOMATABLE_INTENTS:
        return _escalate(
            "Ambiguous sensitive intent requires human review",
            ["ambiguity_on_sensitive_intent"]
        )

    if primary_intent == "loan" and risk_level == "high":
        return {
            "resolution_mode": "GUIDED_RESPONSE",
            "reason": "High-risk loan queries require cautious guidance",
            "risk_factors": ["high_risk_loan"],
            "selected_response_type": "guided_response"
        }

    if restricted_actions:
        return {
            "resolution_mode": "GUIDED_RESPONSE",
            "reason": "Policy restrictions limit actions",
            "risk_factors": ["policy_constraints_present"],
            "selected_response_type": "guided_response"
        }

    if confidence < CONFIDENCE_THRESHOLD and primary_intent in NON_AUTOMATABLE_INTENTS:
        return _escalate(
            "Low confidence on sensitive intent",
            ["low_confidence_sensitive_intent"]
        )

    return {
        "resolution_mode": "GUIDED_RESPONSE",
        "reason": "Low to medium risk and policy compliant",
        "risk_factors": ["safe_to_guide"],
        "selected_response_type": "guided_response"
    }


def _escalate(reason: str, risk_factors: list) -> dict:
    return {
        "resolution_mode": "ESCALATE_TO_HUMAN",
        "reason": reason,
        "risk_factors": risk_factors,
        "selected_response_type": "escalation_response"
    }
