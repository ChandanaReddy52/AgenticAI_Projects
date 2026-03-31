# docbook_tools.py
import uuid
from datetime import datetime
from data_store import get_active_doctors_by_specialty, get_available_slots_by_doctor_id, mark_slot_as_booked, append_booking_history
from langchain.tools import tool


@tool
def FindDoctorsTool(specialty: str):
    """
    Return active doctors for a given specialty.
    """
    results = get_active_doctors_by_specialty(specialty)

    return {
        "specialty": specialty,
        "count": len(results),
        "doctors": [
            {
                "doctor_id": d["doctor_id"],
                "doctor_name": d["doctor_name"]
            }
            for d in results
        ]
    }

@tool
def CheckAvailabilityTool(doctor_id: str):
    """
    Return available appointment slots for a doctor.
    """
    slots = get_available_slots_by_doctor_id(doctor_id)

    return {
        "doctor_id": doctor_id,
        "available_slots": [
            {
                "slot_id": s["slot_id"],
                "date": s["date"],
                "time": s["time"]
            }
            for s in slots
        ]
    }


@tool
def BookAppointmentTool(slot_id: str, patient_name: str):
    """
    Book an appointment for a given slot.
    """
    slot = mark_slot_as_booked(slot_id)

    if not slot:
        return {
            "success": False,
            "error": "Slot not found or already booked"
        }

    booking = {
        "booking_id": f"B{uuid.uuid4().hex[:8]}",
        "slot_id": slot_id,
        "doctor_id": slot["doctor_id"],
        "patient_name": patient_name,
        "booked_at": datetime.utcnow().isoformat(),
        "status": "BOOKED"
    }

    append_booking_history(booking)

    return {
        "success": True,
        "booking": booking
    }
