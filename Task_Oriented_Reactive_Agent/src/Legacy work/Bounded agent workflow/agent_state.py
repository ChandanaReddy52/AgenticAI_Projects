# agent_state.py - explicit application state task memory
# short term memory - single session scoped
from enum import Enum
from typing import Optional, List, Dict


class BookingPhase(Enum):
    START = "START"
    SPECIALTY_SELECTED = "SPECIALTY_SELECTED"
    DOCTOR_SELECTED = "DOCTOR_SELECTED"
    SLOT_SELECTED = "SLOT_SELECTED"
    CONFIRMATION_PENDING = "CONFIRMATION_PENDING"
    BOOKED = "BOOKED"


def init_state():
    return {
        "phase": BookingPhase.START,

        # Task memory (short-term)
        "specialty": None,
        "doctor_id": None,
        "slot_id": None,

        # Cached data (derived, not user intent)
        "available_doctors": [],
        "available_slots": []
    }

