"""
V1 — Direct prompting.
Simplest approach: just tell it what to do.
Limitation: no structure enforcement, reasoning not visible.
"""

SYSTEM_PROMPT = """You are a support intelligence agent for GlobalFoods Inc.
You analyze support tickets and customer data to surface risks and recommend actions.
Always base your answers on the provided data. Never fabricate information."""


def analyze_ticket_prompt(ticket: dict, customer: dict) -> str:
    return f"""Analyze this support ticket and provide a root cause and recommended action.

TICKET:
ID: {ticket['id']}
Title: {ticket['title']}
Description: {ticket['description']}
Priority: {ticket['priority']}
Status: {ticket['status']}
Tags: {', '.join(ticket.get('tags', []))}

CUSTOMER:
Name: {customer.get('name', 'Unknown')}
ARR: ${customer.get('arr', 0):,}
Health Score: {customer.get('health', 0)}/100

Provide: root cause, business impact, recommended action."""


def detect_patterns_prompt(tickets: list, window: str) -> str:
    ticket_summaries = "\n".join([
        f"- {t['id']} [{t['priority']}] {t['title']} | tags: {', '.join(t.get('tags',[]))}"
        for t in tickets
    ])
    return f"""Identify recurring patterns across these {window} tickets:

{ticket_summaries}

List the top patterns you see."""


def customer_risk_prompt(customers: list, ticket_counts: dict) -> str:
    cust_summaries = "\n".join([
        f"- {c['name']}: ARR ${c['arr']:,}, Health {c['health']}/100, "
        f"Open tickets: {ticket_counts.get(c['id'], {}).get('open', 0)}, "
        f"Critical: {ticket_counts.get(c['id'], {}).get('critical', 0)}"
        for c in customers
    ])
    return f"""Rank these customers by churn risk:

{cust_summaries}

Rank from highest to lowest risk with brief reasoning."""


def sla_risk_prompt(at_risk_tickets: list) -> str:
    summaries = "\n".join([
        f"- {t['ticket_id']}: {t['hours_until_breach']}h remaining, "
        f"priority {t['priority']}, customer {t['customer_name']} (${t['arr']:,} ARR)"
        for t in at_risk_tickets
    ])
    return f"""These tickets are approaching SLA breach:

{summaries}

Summarize the risk and recommend immediate actions."""