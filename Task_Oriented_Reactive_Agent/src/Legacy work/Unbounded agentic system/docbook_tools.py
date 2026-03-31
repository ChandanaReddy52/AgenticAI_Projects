# docbook_tools.py
import uuid
from datetime import datetime
from data_store import mark_slot_as_booked, append_booking_history
from langchain.tools import tool


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
