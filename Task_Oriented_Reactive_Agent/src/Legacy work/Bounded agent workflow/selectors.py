# selctors.py - Selection is mechanical, not LLM-guessed.
def select_doctor_from_input(text, doctors):
    t = text.lower()
    for i, d in enumerate(doctors, start=1):
        if f"option {i}" in t or t == str(i) or d["doctor_name"].lower() in t:
            return d["doctor_id"]
    return None

def select_slot_from_input(text, slots):
    t = text.lower().replace(" ", "")
    for i, s in enumerate(slots, start=1):
        time = s["time"].lower().replace(":00", "")
        if f"option {i}" in t or time in t:
            return s["slot_id"]
    return None
