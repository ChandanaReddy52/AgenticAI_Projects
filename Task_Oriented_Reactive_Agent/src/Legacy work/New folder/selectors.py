# selctors.py - Selection is mechanical, not LLM-guessed.
import re

def normalize(text):
    return re.sub(r"[^a-z]", "", text.lower())

def select_doctor_from_input(text, doctors):
    t = normalize(text)

    for i, d in enumerate(doctors, start=1):
        name = normalize(d["doctor_name"])          # drsmith
        lastname = normalize(d["doctor_name"].split()[-1])  # smith

        # option number
        if str(i) == text.strip():
            return d["doctor_id"]

        if f"option{i}" in t:
            return d["doctor_id"]

        # full name match
        if name in t:
            return d["doctor_id"]

        # last name match
        if lastname in t:
            return d["doctor_id"]

    return None


# Normalize time inputs like "3pm", "15:00", "3:00 pm" to "15:00"

def select_slot_from_input(text, slots):
    t = text.lower()

    # 4pm, 4 pm, 16, 16:00
    hour_match = re.search(r"(\d{1,2})\s*(am|pm)?", t)
    if not hour_match:
        return None

    hour = int(hour_match.group(1))
    period = hour_match.group(2)

    if period == "pm" and hour < 12:
        hour += 12

    for s in slots:
        slot_hour = int(s["time"].split(":")[0])
        if slot_hour == hour:
            return s["slot_id"]

    return None
