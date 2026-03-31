import re


def normalize_time(text):
    text = text.lower().replace(" ", "")
    text = text.replace("pm", ":00").replace("am", ":00")
    return text


def resolve_slot_v2(user_text, state):
    if not state["available_slots"]:
        return None

    text = user_text.lower()

    # Step 1: resolve doctor
    doctor_id = None

    for i, doc in enumerate(state["available_doctors"], start=1):
        if f"option {i}" in text or doc["doctor_name"].lower() in text:
            doctor_id = doc["doctor_id"]
            break

    if not doctor_id:
        return None

    # Step 2: resolve slot for that doctor
    doctor_slots = [
        s for s in state["available_slots"]
        if s["doctor_id"] == doctor_id
    ]

    matches = []
    for slot in doctor_slots:
        time_norm = normalize_time(slot["time"])
        if time_norm in normalize_time(text):
            matches.append(slot)

    if len(matches) == 1:
        return {
            "doctor_id": doctor_id,
            "slot_id": matches[0]["slot_id"]
        }

    return None
