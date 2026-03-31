# agent_state.py - explicit application state task memory
# short term memory - single session scoped
from enum import Enum


class BookingPhase(Enum):
    START = "START"
    SPECIALTY_SELECTED = "SPECIALTY_SELECTED"
    DOCTOR_SELECTED = "DOCTOR_SELECTED"
    SLOT_SELECTED = "SLOT_SELECTED"
    CONFIRMATION_PENDING = "CONFIRMATION_PENDING"
    AWAITING_PATIENT_NAME = "AWAITING_PATIENT_NAME"
    BOOKED = "BOOKED"


def init_state():
    return {
        "phase": BookingPhase.START,

        # Task memory
        "specialty": None,
        "doctor_id": None,
        "slot_id": None,
        "patient_name": None,

        # Cached data
        "available_doctors": [],
        "available_slots": [],

        # 🔑 NEW: data readiness flags
        "doctors_loaded": False,
        "slots_loaded": False
    }


