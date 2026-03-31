# state_sync.py - synchronizes agent outputs with application state
def sync_state_from_agent(state, agent_output):
    """
    Merge tool outputs into application state.
    """
    if "available_doctors" in agent_output:
        state["available_doctors"] = agent_output["available_doctors"]

    if "available_slots" in agent_output:
        state["available_slots"] = agent_output["available_slots"]

    return state
