# agent_intent.py - Define the Intent Schema (Brain(LLM) → Kernel(APP))
from enum import Enum
from typing import Optional
from dataclasses import dataclass


class IntentType(Enum):
    SET_SPECIALTY = "SET_SPECIALTY"
    SELECT_DOCTOR = "SELECT_DOCTOR"
    SELECT_SLOT = "SELECT_SLOT"
    SET_PATIENT_NAME = "SET_PATIENT_NAME"
    CONFIRM = "CONFIRM"
    BOOK = "BOOK"
    UNKNOWN = "UNKNOWN"


@dataclass
class Intent:
    type: IntentType
    specialty: Optional[str] = None
    doctor_id: Optional[str] = None
    slot_id: Optional[str] = None
    patient_name: Optional[str] = None
