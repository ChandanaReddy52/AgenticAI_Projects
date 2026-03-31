#data_store.py
import os
import csv
from pathlib import Path

# ------------------------
# Path setup
# ------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = Path(BASE_DIR) / "data" / "dataset_v1_docbook"

def load_csv(filename):
    with open(DATA_DIR / filename, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

# Load datasets
doctors = load_csv("doctors.csv")
appointment_slots = load_csv("appointment_slots.csv")
booking_history = load_csv("booking_history.csv")


# ----------------------------------------
# Data Access Layer
# ----------------------------------------

#Adding helper functions instead of letting tools touch raw lists.
def get_active_doctors_by_specialty(specialty):
    return [
        d for d in doctors
        if d["specialty"].lower() == specialty.lower()
        and d["active"].lower() == "true"
    ]

def get_available_slots_by_doctor_id(doctor_id):
    return [
        s for s in appointment_slots
        if s["doctor_id"] == doctor_id and s["status"] == "AVAILABLE"
    ]

def mark_slot_as_booked(slot_id):
    for s in appointment_slots:
        if s["slot_id"] == slot_id and s["status"] == "AVAILABLE":
            s["status"] = "BOOKED"
            return s
    return None

def append_booking_history(record):
    booking_history.append(record)
