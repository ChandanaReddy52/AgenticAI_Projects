# selection_parser.py
def resolve_slot_selection(user_input: str, available_slots: list):
    text = user_input.lower()

    # index-based selection
    for i, slot in enumerate(available_slots, start=1):
        if f"option {i}" in text or f"{i}" == text.strip():
            return slot["slot_id"]

    # time-based selection
    for slot in available_slots:
        time = slot["time"].lower().replace(":00", "")
        if time in text:
            return slot["slot_id"]

    return None

def resolve_doctor_selection(user_input: str, available_doctors: list):
    text = user_input.lower()
    for d in available_doctors:
        if d["doctor_name"].lower() in text:
            return d["doctor_id"]
    return None
