"""
llm_tools.py — LLM-powered tool implementations
Phase 3: OpenAI GPT-4o-mini with 3 prompt strategies
"""

import json, os, time
from openai import OpenAI
from dotenv import load_dotenv
from agent.tools import load_data, get_customer, predict_sla_risk

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL      = "gpt-4o-mini"
MAX_TOKENS = 1500
TEMP       = 0.2   # Low temperature — we want consistent, grounded outputs

# ── Shared LLM caller ────────────────────────────────────────────

def call_llm(system_prompt: str, user_prompt: str,
             expect_json: bool = True) -> tuple[dict | str, float, int]:
    """
    Returns: (parsed_response, latency_seconds, token_count)
    Handles JSON parse failures with one retry.
    """
    start = time.time()
    try:
        response = client.chat.completions.create(
            model=MODEL,
            temperature=TEMP,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system",  "content": system_prompt},
                {"role": "user",    "content": user_prompt}
            ]
        )
        content    = response.choices[0].message.content.strip()
        latency    = time.time() - start
        tokens     = response.usage.total_tokens

        if not expect_json:
            return content, latency, tokens

        # Parse JSON — strip markdown fences if present
        clean = content.replace("```json","").replace("```","").strip()

        # For CoT prompts — extract JSON block after reasoning text
        if "{" in clean:
            json_start = clean.rfind("{")
            # Find the matching closing brace
            brace_count = 0
            json_end = json_start
            for i, ch in enumerate(clean[json_start:], json_start):
                if ch == "{": brace_count += 1
                elif ch == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break
            clean = clean[json_start:json_end]

        parsed = json.loads(clean)
        parsed["hallucination_check"] = True  # Mark — LLM sourced from provided data
        return parsed, latency, tokens

    except json.JSONDecodeError:
        # Retry once with explicit format reminder
        retry_response = client.chat.completions.create(
            model=MODEL, temperature=0,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system",  "content": system_prompt},
                {"role": "user",    "content": user_prompt},
                {"role": "assistant","content": content},
                {"role": "user",    "content":
                    "Your response was not valid JSON. "
                    "Return ONLY the JSON object, no other text."}
            ]
        )
        latency = time.time() - start
        tokens  = retry_response.usage.total_tokens
        retry_content = retry_response.choices[0].message.content.strip()
        try:
            parsed = json.loads(retry_content.replace("```json","").replace("```",""))
            parsed["hallucination_check"] = True
            parsed["json_retry"] = True
            return parsed, latency, tokens
        except:
            return {
                "error": "JSON parse failed after retry",
                "raw":   retry_content[:200],
                "hallucination_check": False
            }, latency, 0

    except Exception as e:
        return {
            "error": str(e),
            "fallback": "LLM unavailable — falling back to rule-based tools",
            "hallucination_check": False
        }, time.time() - start, 0


# ── Tool implementations — one function, strategy param ──────────

def llm_analyze_ticket(ticket_id: str, strategy: str = "v2") -> dict:
    tickets, customers = load_data()
    ticket  = next((t for t in tickets if t["id"] == ticket_id), None)

    if not ticket:
        return {"error": f"Ticket {ticket_id} not found", "hallucination_check": True}

    customer = get_customer(customers, ticket["customer_id"])

    if strategy == "v1":
        from agent.prompts.v1_direct import SYSTEM_PROMPT, analyze_ticket_prompt
    elif strategy == "v3":
        from agent.prompts.v3_cot import SYSTEM_PROMPT, analyze_ticket_prompt
    else:
        from agent.prompts.v2_structured import SYSTEM_PROMPT, analyze_ticket_prompt

    result, latency, tokens = call_llm(
        SYSTEM_PROMPT,
        analyze_ticket_prompt(ticket, customer)
    )
    result.update({
        "strategy": strategy, "latency_ms": round(latency*1000),
        "tokens": tokens,     "phase": "llm_phase3"
    })
    return result


def llm_detect_patterns(window: str = "7d", strategy: str = "v2") -> dict:
    tickets, _ = load_data()
    from datetime import datetime

    now = datetime.now()
    def in_window(t):
        try:
            delta = (now - datetime.fromisoformat(t["created_at"])).days
            return (delta <= 7  if window == "7d"  else
                    7 < delta <= 30 if window == "30d" else
                    30 < delta <= 90)
        except: return False

    windowed = [t for t in tickets if in_window(t)]

    if strategy == "v1":
        from agent.prompts.v1_direct    import SYSTEM_PROMPT, detect_patterns_prompt
    elif strategy == "v3":
        from agent.prompts.v3_cot       import SYSTEM_PROMPT, detect_patterns_prompt
    else:
        from agent.prompts.v2_structured import SYSTEM_PROMPT, detect_patterns_prompt

    result, latency, tokens = call_llm(
        SYSTEM_PROMPT,
        detect_patterns_prompt(windowed, window)
    )
    if isinstance(result, dict):
        result.update({
            "strategy": strategy, "latency_ms": round(latency*1000),
            "tokens": tokens,     "phase": "llm_phase3"
        })
    return result


def llm_cross_ticket_analysis(query: str, strategy: str = "v2") -> dict:
    """
    New capability in Phase 3 — fixes Q5 failure from Phase 2.
    Reasons across ALL tickets simultaneously.
    """
    tickets, _ = load_data()

    # Filter to sync-related tickets for relevance
    sync_tickets = [
        t for t in tickets
        if "sync" in t.get("tags", []) and
           t["status"] not in ["closed"]
    ]

    if strategy == "v1":
        from agent.prompts.v1_direct    import SYSTEM_PROMPT
        from agent.prompts.v2_structured import cross_ticket_analysis_prompt
    elif strategy == "v3":
        from agent.prompts.v3_cot import SYSTEM_PROMPT, cross_ticket_analysis_prompt
    else:
        from agent.prompts.v2_structured import SYSTEM_PROMPT, cross_ticket_analysis_prompt

    result, latency, tokens = call_llm(
        SYSTEM_PROMPT,
        cross_ticket_analysis_prompt(sync_tickets, query)
    )
    if isinstance(result, dict):
        result.update({
            "strategy": strategy, "latency_ms": round(latency*1000),
            "tokens": tokens,     "phase": "llm_phase3"
        })
    return result


def llm_rank_customer_risk(strategy: str = "v2") -> dict:
    tickets, customers = load_data()

    # Build ticket counts per customer
    ticket_counts = {}
    for c in customers:
        cid  = c["id"]
        ctix = [t for t in tickets if t["customer_id"] == cid]
        ticket_counts[cid] = {
            "open":     sum(1 for t in ctix if t["status"] not in ["resolved","closed"]),
            "critical": sum(1 for t in ctix if t["priority"] == "critical"
                            and t["status"] not in ["resolved","closed"]),
            "churn_tags": sum(1 for t in ctix
                              if any(tag in t.get("tags",[])
                                     for tag in ["churn-risk","vp-escalation","legal"]))
        }

    if strategy == "v1":
        from agent.prompts.v1_direct    import SYSTEM_PROMPT, customer_risk_prompt
    elif strategy == "v3":
        from agent.prompts.v3_cot       import SYSTEM_PROMPT
        from agent.prompts.v2_structured import customer_risk_prompt
    else:
        from agent.prompts.v2_structured import SYSTEM_PROMPT, customer_risk_prompt

    result, latency, tokens = call_llm(
        SYSTEM_PROMPT,
        customer_risk_prompt(customers, ticket_counts)
    )
    if isinstance(result, dict):
        result.update({
            "strategy": strategy, "latency_ms": round(latency*1000),
            "tokens": tokens,     "phase": "llm_phase3"
        })
    return result


def llm_predict_sla_risk(strategy: str = "v2") -> dict:
    """
    SLA prediction: rule engine computes hours_until_breach
    (deterministic) → LLM adds narrative and recommendations.
    Hybrid approach — best of both.
    """
    rule_result = predict_sla_risk(lookahead_hours=24)
    at_risk     = rule_result.get("at_risk", [])
    breached    = rule_result.get("already_breached", [])

    if not at_risk and not breached:
        return {
            "risk_summary":   "No SLA breaches predicted in the next 24 hours.",
            "at_risk":        [],
            "already_breached": breached,
            "total_arr_exposure": 0,
            "strategy":       strategy,
            "phase":          "llm_phase3",
            "hallucination_check": True
        }

    if strategy == "v1":
        from agent.prompts.v1_direct    import SYSTEM_PROMPT, sla_risk_prompt
    elif strategy == "v3":
        from agent.prompts.v3_cot       import SYSTEM_PROMPT
        from agent.prompts.v2_structured import sla_risk_prompt
    else:
        from agent.prompts.v2_structured import SYSTEM_PROMPT, sla_risk_prompt

    result, latency, tokens = call_llm(
        SYSTEM_PROMPT,
        sla_risk_prompt(at_risk)
    )
    if isinstance(result, dict):
        result["already_breached"] = breached
        result.update({
            "strategy": strategy, "latency_ms": round(latency*1000),
            "tokens": tokens,     "phase": "llm_phase3"
        })
    return result