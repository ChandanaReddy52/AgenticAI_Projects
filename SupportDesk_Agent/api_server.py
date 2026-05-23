"""
api_server.py — FastAPI bridge between SupportDesk web app and Python agent
Location: supportdesk_agent/api_server.py

Exposes 5 HTTP endpoints that exactly mirror the 5 AI_API functions
the web app calls in js/ai.js:

  POST /api/analyze-ticket          ← AI_API.analyzeTicket(ticket)
  POST /api/suggest-reply           ← AI_API.suggestReply(ticket)
  POST /api/suggest-priority        ← AI_API.suggestPriority(title, desc)
  POST /api/insights                ← AI_API.generateTimelineInsights(tickets, window)
  POST /api/chat                    ← AI_API.chatWithContext(history, context)

The web app's js/ai.js is updated to call these endpoints instead of
OpenAI directly. The agent's full tool stack (RAG + ChromaDB + LangChain
+ memory + adaptation) runs server-side. The web app is unchanged otherwise.

Run:
  pip install fastapi uvicorn python-multipart
  python api_server.py
  → Server starts at http://localhost:8000

Then update js/ai.js: set AGENT_API_URL = 'http://localhost:8000'
"""

import os, sys, json, time
from datetime import datetime
from typing import Optional

# ── Path setup so agent imports work ──────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ── Load .env before any agent imports ────────────────────────────
def _find_env(start: str):
    current = start
    for _ in range(8):
        c = os.path.join(current, ".env")
        if os.path.isfile(c):
            return c
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None

_env = _find_env(PROJECT_ROOT)
if _env:
    from dotenv import load_dotenv
    load_dotenv(_env)

# ── FastAPI ────────────────────────────────────────────────────────
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Agent imports ──────────────────────────────────────────────────
from agent.adaptive_agent  import run_adaptive_agent, init_adaptive_session
from agent.tools_langchain import (
    analyze_ticket_tool,
    detect_patterns_tool,
    rank_customer_risk_tool,
    predict_sla_risk_tool,
    cross_ticket_analysis_tool,
)
from agent.logger import log_interaction


# ══════════════════════════════════════════════════════════════════
app = FastAPI(
    title="SupportDesk Agent API",
    description="Bridges SupportDesk web app to the Python AI agent",
    version="1.0.0"
)

# Allow the web app (file:// or localhost:any-port) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # tighten to specific origin in production
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# ── Session init ───────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    print(f"[SupportDesk API] Starting up — env: {_env or 'system'}")
    init_adaptive_session()
    print("[SupportDesk API] Agent session initialised")


# ══════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE MODELS
# ══════════════════════════════════════════════════════════════════

class TicketPayload(BaseModel):
    ticket: dict

class ReplyPayload(BaseModel):
    ticket: dict

class PriorityPayload(BaseModel):
    title: str
    description: str

class InsightsPayload(BaseModel):
    tickets: list
    window: str = "7d"          # "7d" | "30d" | "90d"

class ChatPayload(BaseModel):
    history: list               # [{role, content}, ...]
    context: Optional[dict] = None   # {tickets, customers, ...}
    query: Optional[str] = None      # last user message (convenience)


# ══════════════════════════════════════════════════════════════════
# ENDPOINT 1 — Analyze single ticket
# Replaces: AI_API.analyzeTicket(ticket)
# ══════════════════════════════════════════════════════════════════

@app.post("/api/analyze-ticket")
async def analyze_ticket(payload: TicketPayload):
    """
    Analyze a single support ticket using the agent's analyze_ticket tool.
    Returns structured root cause, severity, business impact, and recommendation.
    """
    ticket = payload.ticket
    ticket_id = ticket.get("id", "")

    if not ticket_id:
        raise HTTPException(status_code=400, detail="ticket.id is required")

    start = time.time()
    try:
        result_json = analyze_ticket_tool.func(ticket_id=ticket_id)
        result = json.loads(result_json)

        # Format as plain text for web app (matches AI_API.analyzeTicket return)
        if result.get("not_found"):
            text = (f"Ticket {ticket_id} was not found in the knowledge base. "
                    f"Did you mean: {', '.join(result.get('available_ids', []))}?")
        else:
            text = (
                f"Root cause: {result.get('root_cause_hypothesis', 'Unknown')}. "
                f"Severity: {result.get('severity_assessment', 'unknown')}. "
                f"Business impact: {result.get('business_impact', 'N/A')}. "
                f"Recommended action: {result.get('recommended_action', 'N/A')}."
            )

        _log("analyze_ticket", ticket_id, time.time() - start)
        return {"result": text, "structured": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════
# ENDPOINT 2 — Suggest customer reply
# Replaces: AI_API.suggestReply(ticket)
# ══════════════════════════════════════════════════════════════════

@app.post("/api/suggest-reply")
async def suggest_reply(payload: ReplyPayload):
    """
    Draft a professional customer-facing reply for a ticket.
    Uses the agent's LLM directly (no tool call needed — this is
    a generation task, not a retrieval task).
    """
    ticket = payload.ticket
    start  = time.time()

    try:
        from agent.llm_tools import call_llm

        prompt = (
            f"Draft a professional, empathetic customer-facing support reply. "
            f"Max 80 words. Include: acknowledgment, what we are doing to fix it, "
            f"rough ETA. No placeholders like [Name] or [Date].\n\n"
            f"Ticket: {ticket.get('title', '')}\n"
            f"Description: {ticket.get('description', '')}\n"
            f"Priority: {ticket.get('priority', 'medium')}\n"
            f"Status: {ticket.get('status', 'open')}\n\n"
            f"Reply text only. No subject line, no preamble."
        )

        system = "You are a professional customer support writer. Reply only with the draft text."
        result, _, _ = call_llm(system, prompt)

        reply_text = result if isinstance(result, str) else str(result)
        _log("suggest_reply", ticket.get("id", ""), time.time() - start)
        return {"result": reply_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════
# ENDPOINT 3 — Suggest priority and tags
# Replaces: AI_API.suggestPriority(title, description)
# ══════════════════════════════════════════════════════════════════

@app.post("/api/suggest-priority")
async def suggest_priority(payload: PriorityPayload):
    """
    Classify a ticket and suggest priority, category, and tags.
    Returns JSON with priority, category, tags[], reason.
    """
    start = time.time()
    try:
        from agent.llm_tools import call_llm

        system = ("You are a support ticket classifier. "
                  "Always respond with valid JSON only — "
                  "no markdown, no backticks, no explanation.")

        prompt = (
            f'Classify this support ticket. Return ONLY this JSON:\n\n'
            f'{{"priority":"critical|high|medium|low",'
            f'"category":"Bug|Feature Request|Feature Upgrade|Incident|Query",'
            f'"tags":["tag1","tag2","tag3"],'
            f'"reason":"one sentence"}}\n\n'
            f"Title: {payload.title}\n"
            f"Description: {payload.description}"
        )

        result, _, _ = call_llm(system, prompt)

        if isinstance(result, dict):
            _log("suggest_priority", payload.title[:40], time.time() - start)
            return result

        # Fallback parse
        if isinstance(result, str):
            try:
                parsed = json.loads(result.replace("```json", "").replace("```", "").strip())
                _log("suggest_priority", payload.title[:40], time.time() - start)
                return parsed
            except Exception:
                pass

        raise HTTPException(status_code=500, detail="Could not parse priority classification")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════
# ENDPOINT 4 — Timeline-windowed insights
# Replaces: AI_API.generateTimelineInsights(tickets, window)
# This is the main upgrade — uses all 5 agent tools instead of
# a single raw LLM call
# ══════════════════════════════════════════════════════════════════

@app.post("/api/insights")
async def generate_insights(payload: InsightsPayload):
    """
    Generate AI Insights Hub data for a time window using the full agent tool stack.

    Phase 5 agent tools are called directly:
      - detect_patterns      → patterns[]
      - rank_customer_risk   → at_risk_customers[] (deterministic)
      - predict_sla_risk     → sla_at_risk[]
      - cross_ticket_analysis → exec_summary + root cause

    Returns the same JSON structure as AI_API.generateTimelineInsights()
    so the web app renders identically — no frontend changes needed.
    """
    window  = payload.window
    start   = time.time()

    try:
        # ── detect_patterns ────────────────────────────────────────
        patterns_raw  = detect_patterns_tool.func(window=window, min_frequency=2)
        patterns_data = json.loads(patterns_raw)

        # Normalise to list — web app expects patterns[]
        if isinstance(patterns_data, dict) and "patterns" not in patterns_data:
            patterns_list = [patterns_data] if patterns_data.get("pattern_name") else []
        else:
            patterns_list = patterns_data.get("patterns", [patterns_data])

        # Map agent schema → web app schema
        web_patterns = []
        for p in patterns_list:
            web_patterns.append({
                "title":      p.get("pattern_name", p.get("title", "Unknown pattern")),
                "description": (p.get("root_cause_signal", "") + " " +
                                p.get("recommendation", "")).strip(),
                "ticket_ids": p.get("ticket_ids", []),
                "severity":   _severity_from_trend(p.get("trend", "stable")),
            })

        # ── rank_customer_risk (deterministic) ─────────────────────
        risk_raw  = rank_customer_risk_tool.func(sort_by="risk_score", top_n=5)
        risk_data = json.loads(risk_raw)
        ranked    = risk_data.get("ranked_customers", [])

        at_risk = []
        for c in ranked:
            if c.get("risk_label") in ["critical", "high"]:
                at_risk.append({
                    "customer":    c["name"],
                    "reason":      c.get("recommended_action", ""),
                    "arr_at_risk": f"${c['arr']/1000:.0f}K",
                    "urgency":     c["risk_label"],
                })

        # ── predict_sla_risk ───────────────────────────────────────
        sla_raw  = predict_sla_risk_tool.func(lookahead_hours=24)
        sla_data = json.loads(sla_raw)

        sla_at_risk = []
        # Already-breached
        for i in range(sla_data.get("already_breached_count", 0)):
            sla_at_risk.append({
                "ticket_id": f"TKT-BREACH-{i+1}",
                "title":     "SLA breached",
                "hours_left": -1,
                "action":    "Address immediately",
            })
        # At-risk (within lookahead)
        for item in sla_data.get("at_risk", []):
            sla_at_risk.append({
                "ticket_id": item.get("ticket_id", ""),
                "title":     item.get("business_impact", "")[:60],
                "hours_left": -item.get("hours_until_breach", 1),
                "action":    item.get("recommended_action", ""),
            })

        # ── cross_ticket_analysis for exec summary ─────────────────
        query = {
            "7d":  "What is the most urgent situation in the support queue right now?",
            "30d": "What patterns are forming across the support queue this month?",
            "90d": "What is the overall health of the support queue this quarter?",
        }.get(window, "Summarise the current support queue state.")

        cross_raw  = cross_ticket_analysis_tool.func(query=query)
        cross_data = json.loads(cross_raw)

        exec_summary = (
            f"{cross_data.get('shared_root_cause', '')} "
            f"{cross_data.get('pattern_description', '')}"
        ).strip()

        top_recommendation = cross_data.get("recommended_fix", "")

        # ── Sentiment scores (simple heuristic — no tool needed) ───
        # Web app expects sentiment_scores[] with ticket_id, urgency_score,
        # sentiment, signal. We derive from the supporting tickets list.
        sentiment_scores = []
        for tid in cross_data.get("supporting_tickets", []):
            sentiment_scores.append({
                "ticket_id":    tid,
                "urgency_score": 7 if window == "7d" else 5 if window == "30d" else 3,
                "sentiment":    "frustrated" if window == "7d" else "neutral",
                "signal":       cross_data.get("shared_root_cause", "")[:60],
            })

        elapsed = round((time.time() - start) * 1000)
        _log("insights", window, time.time() - start)

        return {
            "exec_summary":      exec_summary,
            "top_recommendation": top_recommendation,
            "patterns":          web_patterns,
            "at_risk_customers": at_risk,
            "sla_at_risk":       sla_at_risk,
            "sentiment_scores":  sentiment_scores,
            "window":            window,
            "ticket_count":      len(payload.tickets),
            "_agent_latency_ms": elapsed,
            "_source":           "supportdesk_agent_v8",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════
# ENDPOINT 5 — Conversational chat (Insights Hub Q&A)
# Replaces: AI_API.chatWithContext(conversationHistory, context)
# ══════════════════════════════════════════════════════════════════

@app.post("/api/chat")
async def chat_with_context(payload: ChatPayload):
    """
    Conversational Q&A using the full adaptive agent with memory.
    The agent uses its tool stack to answer — not just the LLM.
    Conversation history is maintained server-side via memory_agent.
    """
    start = time.time()

    # Extract the last user message from history or payload.query
    query = payload.query
    if not query and payload.history:
        last = payload.history[-1]
        if last.get("role") == "user":
            query = last.get("content", "")

    if not query:
        raise HTTPException(status_code=400, detail="No user query found in history or query field")

    try:
        # Use the full Phase 7 adaptive agent — tool calling + memory + adaptation
        response = run_adaptive_agent(query, verbose=False)

        # Strip the footer ([Phase 7 Adaptive | ...]) before returning to web app
        if "\n[Phase" in response:
            response = response[:response.rfind("\n[Phase")]

        _log("chat", query[:60], time.time() - start)
        return {"result": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ══════════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    """Quick health check — call from web app on startup to verify bridge."""
    from deployment.health_check import (
        check_env, check_data_files, check_chromadb, check_memory_file
    )
    checks = {}
    checks["env"],    _ = check_env()
    checks["data"],   _ = check_data_files()
    checks["chroma"], _ = check_chromadb()
    checks["memory"], _ = check_memory_file()

    all_ok = all(checks.values())
    return {
        "status":  "healthy" if all_ok else "degraded",
        "checks":  checks,
        "agent":   "SupportDesk Agent v8",
        "time":    datetime.now().isoformat(),
    }


# ══════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════

def _severity_from_trend(trend: str) -> str:
    return {"accelerating": "high", "stable": "medium", "declining": "low"}.get(
        trend, "medium"
    )


def _log(endpoint: str, detail: str, latency: float):
    try:
        log_interaction(
            query=detail,
            intent=f"api_{endpoint}",
            tool=endpoint,
            response={"source": "api_server"},
            latency=latency,
            phase="api_bridge",
            notes=f"endpoint:{endpoint} latency:{round(latency*1000)}ms"
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    print("\nSupportDesk Agent API Bridge")
    print("="*40)
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Env file:     {_env or 'not found — using system env'}")
    print("Endpoints:")
    print("  POST /api/analyze-ticket")
    print("  POST /api/suggest-reply")
    print("  POST /api/suggest-priority")
    print("  POST /api/insights")
    print("  POST /api/chat")
    print("  GET  /api/health")
    print("="*40)
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=False)
