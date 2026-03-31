# agent_reducer.py - Defines Allowed Transitions (kernel Guarded) to prevent loops
from agent_state import BookingPhase
from agent_intent import IntentType

def reduce_state(state, intent):
    # 🔑 FIX: normalize intent type
    intent_type = intent["type"]
    if isinstance(intent_type, str):
        intent_type = IntentType(intent_type)

    new_state = state.copy()

    # ----------------------------
    # SET SPECIALTY
    # ----------------------------
    if intent_type == IntentType.SET_SPECIALTY:
        new_state["specialty"] = intent["specialty"]
        new_state["phase"] = BookingPhase.SPECIALTY_SELECTED
        new_state["available_doctors"] = []
        new_state["available_slots"] = []
        new_state["doctor_id"] = None
        new_state["slot_id"] = None
        return new_state

    # ----------------------------
    # SELECT DOCTOR
    # ----------------------------
    if intent_type == IntentType.SELECT_DOCTOR:
        new_state["doctor_id"] = intent["doctor_id"]
        new_state["phase"] = BookingPhase.DOCTOR_SELECTED
        new_state["available_slots"] = []
        return new_state

    # ----------------------------
    # SELECT SLOT
    # ----------------------------
    if intent_type == IntentType.SELECT_SLOT:
        new_state["slot_id"] = intent["slot_id"]
        new_state["phase"] = BookingPhase.BOOKED
        return new_state

    # ----------------------------
    # SET PATIENT NAME
    # ----------------------------
    if intent_type == IntentType.SET_PATIENT_NAME:
        new_state["patient_name"] = intent["patient_name"]
        new_state["phase"] = BookingPhase.BOOKED
        return new_state
