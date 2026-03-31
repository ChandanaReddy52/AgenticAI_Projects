from docbook_tools import FindDoctorsTool, CheckAvailabilityTool, BookAppointmentTool

#Find doctors by specialty
print("=== FIND DOCTORS ===")
result = FindDoctorsTool.invoke({"specialty": "Dermatology"})
print(result)

#Pick doctor → check availability
doctor_id = result["doctors"][0]["doctor_id"]

print("\n=== CHECK AVAILABILITY ===")
slots = CheckAvailabilityTool.invoke({"doctor_id": doctor_id})
print(slots)

#Book a slot
from docbook_tools import BookAppointmentTool

slot_id = slots["available_slots"][0]["slot_id"]

print("\n=== BOOK APPOINTMENT ===")
booking = BookAppointmentTool.invoke({
    "slot_id": slot_id,
    "patient_name": "Test User"
})
print(booking)

#Re-check availability (critical test)
print("\n=== RECHECK AVAILABILITY ===")
slots_after = CheckAvailabilityTool.invoke({"doctor_id": doctor_id})
print(slots_after)

