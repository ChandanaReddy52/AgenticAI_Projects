# docbook_state.py - application state management for DocBook agent
# source of truth for the booking flow.
def init_booking_state():
    return {
        "intent": "BOOK_APPOINTMENT",
        "specialty": None,

        "available_doctors": [],
        "selected_doctor_id": None,

        "available_slots": [],
        "selected_slot_id": None,

        "confirmed": False
    }


