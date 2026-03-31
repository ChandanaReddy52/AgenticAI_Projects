# intent.py - defines IntentType enum and Intent dataclass for DocBook agent
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class IntentType(Enum):
    SET_SPECIALTY = "SET_SPECIALTY"
    SELECT_DOCTOR = "SELECT_DOCTOR"
    SELECT_SLOT = "SELECT_SLOT"
    CONFIRM_BOOKING = "CONFIRM_BOOKING"
    RESTART = "RESTART"
    UNKNOWN = "UNKNOWN"


@dataclass
class Intent:
    type: IntentType
    specialty: Optional[str] = None
    doctor_id: Optional[str] = None
    slot_id: Optional[str] = None
