# agent_reducer.py - Defines Allowed Transitions (kernel Guarded) to prevent loops
from agent_state import BookingPhase


def reduce_state(state, intent):
    phase = state["phase"]

    if intent["type"] == "SET_SPECIALTY":
        state["specialty"] = intent["specialty"]
        state["doctor_id"] = None
        state["slot_id"] = None
        state["available_doctors"] = []
        state["available_slots"] = []
        state["phase"] = BookingPhase.SPECIALTY_SELECTED

    elif intent["type"] == "SELECT_DOCTOR" and phase == BookingPhase.SPECIALTY_SELECTED:
        state["doctor_id"] = intent["doctor_id"]
        state["slot_id"] = None
        state["available_slots"] = []
        state["phase"] = BookingPhase.DOCTOR_SELECTED

    elif intent["type"] == "SELECT_SLOT" and phase == BookingPhase.DOCTOR_SELECTED:
        state["slot_id"] = intent["slot_id"]
        state["phase"] = BookingPhase.SLOT_SELECTED

    elif intent["type"] == "CONFIRM" and phase == BookingPhase.SLOT_SELECTED:
        state["phase"] = BookingPhase.CONFIRMATION_PENDING

    elif intent["type"] == "BOOK" and phase == BookingPhase.CONFIRMATION_PENDING:
        state["phase"] = BookingPhase.BOOKED

    return state
