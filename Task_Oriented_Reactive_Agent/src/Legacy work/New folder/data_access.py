# data_access.py - Data is fetched deterministically from state
from data_store import (
    get_active_doctors_by_specialty,
    get_available_slots_by_doctor_id,
    mark_slot_as_booked,
    log_booking
)

def fetch_doctors(state):
    if state["specialty"] and not state["doctors_loaded"]:
        state["available_doctors"] = get_active_doctors_by_specialty(state["specialty"])
        state["doctors_loaded"] = True

def fetch_slots(state):
    if state["doctor_id"]:
        state["available_slots"] = get_available_slots_by_doctor_id(state["doctor_id"])
        state["slots_loaded"] = True


def book_slot(state):
    success = mark_slot_as_booked(state["slot_id"])
    if success:
        log_booking(
            doctor_id=state["doctor_id"],
            slot_id=state["slot_id"],
            specialty=state["specialty"],
            patient_name=state["patient_name"]
        )
    return success
