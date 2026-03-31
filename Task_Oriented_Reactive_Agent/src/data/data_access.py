# data_access.py - Data is fetched through REST APIs using HTTP calls
import requests

BASE_URL = "http://127.0.0.1:5000"

# Data access functions that interact with the REST API
# Fetch active doctors by specialty
def fetch_doctors(state):
    if state["specialty"] and not state["doctors_loaded"]:
        try:
            response = requests.get(
                f"{BASE_URL}/doctors",
                params={"specialty": state["specialty"]}
            )
        except requests.exceptions.ConnectionError:
            print("⚠️ API server not running")
            return

        if response.status_code == 200:
            state["available_doctors"] = response.json()["doctors"]
            state["doctors_loaded"] = True



# Fetch available slots for the selected doctor
def fetch_slots(state):
    if state["doctor_id"]:
        try:
            response = requests.get(
                f"{BASE_URL}/slots",
                params={"doctor_id": state["doctor_id"]}
            )
        except requests.exceptions.ConnectionError:
            print("⚠️ API server not running")
            return

        if response.status_code == 200:
            state["available_slots"] = response.json()["slots"]
            state["slots_loaded"] = True


# Book the selected slot
def book_slot(state):
    payload = {
        "doctor_id": state["doctor_id"],
        "slot_id": state["slot_id"],
        "patient_name": state["patient_name"],
        "specialty": state["specialty"]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/book", json=payload)
    except requests.exceptions.ConnectionError:
        print("⚠️ API server not running")
        return False

    return response.status_code == 200
