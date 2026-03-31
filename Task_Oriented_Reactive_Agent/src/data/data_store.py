#data_store.py
import os
import csv
import uuid
from pathlib import Path
from datetime import datetime

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

BOOKING_HISTORY_FILE = DATA_DIR / "booking_history.csv" # BOOKING_HISTORY_FILE -> append-only audit log
booking_history_records = load_csv("booking_history.csv") # booking_history_records -> in-memory snapshot (read-only)



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

def save_csv(filename, rows, fieldnames):
    with open(DATA_DIR / filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def mark_slot_as_booked(slot_id):
    updated = False

    for s in appointment_slots:
        if s["slot_id"] == slot_id and s["status"] == "AVAILABLE":
            s["status"] = "BOOKED"
            updated = True
            break

    if updated:
        save_csv(
            "appointment_slots.csv",
            appointment_slots,
            fieldnames=appointment_slots[0].keys()
        )
        return True

    return False

def log_booking(doctor_id, slot_id, specialty, patient_name):
    with open(BOOKING_HISTORY_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            str(uuid.uuid4()),
            patient_name,
            specialty,
            doctor_id,
            slot_id,
            datetime.utcnow().isoformat(),
            "CONFIRMED"
        ])




