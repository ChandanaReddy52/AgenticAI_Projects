from intent import IntentType
from docbook_state import init_booking_state


def reduce_state(state, intent):
    if intent.type == IntentType.RESTART:
        return init_booking_state()

    if intent.type == IntentType.SET_SPECIALTY:
        state["specialty"] = intent.specialty
        state["available_doctors"] = []
        state["selected_doctor_id"] = None
        state["available_slots"] = []
        state["selected_slot_id"] = None
        state["confirmed"] = False

    elif intent.type == IntentType.SELECT_DOCTOR:
        state["selected_doctor_id"] = intent.doctor_id
        state["available_slots"] = []
        state["selected_slot_id"] = None
        state["confirmed"] = False

    elif intent.type == IntentType.SELECT_SLOT:
        state["selected_doctor_id"] = intent.doctor_id
        state["selected_slot_id"] = intent.slot_id

    elif intent.type == IntentType.CONFIRM_BOOKING:
        state["confirmed"] = True

    return state
