from agent_intent import Intent, IntentType
from normalizers import normalize_specialty
from agent_state import BookingPhase


def llm_brain(user_text: str, state: dict):
    text = user_text.lower().strip()
    phase = state["phase"]

    # -------- PHASE: START --------
    if phase == BookingPhase.START:
        spec = normalize_specialty(text)
        if spec:
            return (
                Intent(IntentType.SET_SPECIALTY, specialty=spec),
                f"Sure. I will help you book a {spec} appointment."
            )
        return (
            Intent(IntentType.UNKNOWN),
            "Which specialty would you like to book an appointment with?"
        )

    # -------- PHASE: SPECIALTY_SELECTED --------
    if phase == BookingPhase.SPECIALTY_SELECTED:
        doctors = state["available_doctors"]
        if not doctors:
            return (
                Intent(IntentType.UNKNOWN),
                "Looking up available doctors for this specialty."
            )

        doctor_list = "\n".join(
            [f"{i+1}. {d['doctor_name']}" for i, d in enumerate(doctors)]
        )

        return (
            Intent(IntentType.UNKNOWN),
            f"Here are the available doctors:\n{doctor_list}\nPlease select one."
        )

    # -------- PHASE: DOCTOR_SELECTED --------
    if phase == BookingPhase.DOCTOR_SELECTED:
        slots = state["available_slots"]
        if not slots:
            return (
                Intent(IntentType.UNKNOWN),
                "Checking available time slots."
            )

        slot_list = "\n".join(
            [f"{i+1}. {s['date']} at {s['time']}" for i, s in enumerate(slots)]
        )

        return (
            Intent(IntentType.UNKNOWN),
            f"Available time slots:\n{slot_list}\nPlease select a slot."
        )

    # -------- PHASE: SLOT_SELECTED --------
    if phase == BookingPhase.SLOT_SELECTED:
        if text in {"yes", "confirm", "ok", "okay"}:
            return (
                Intent(IntentType.CONFIRM),
                "Great. I will confirm your booking."
            )

        return (
            Intent(IntentType.UNKNOWN),
            "Please confirm if you want to book this appointment."
        )

    # -------- PHASE: CONFIRMATION_PENDING --------
    if phase == BookingPhase.CONFIRMATION_PENDING:
        return (
            Intent(IntentType.BOOK),
            "Booking your appointment now."
        )

    return (
        Intent(IntentType.UNKNOWN),
        "I didn’t quite understand that."
    )
