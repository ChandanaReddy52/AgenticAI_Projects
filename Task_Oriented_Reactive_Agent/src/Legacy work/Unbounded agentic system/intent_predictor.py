# intent_predictor.py - predicts user intent based on input and current state
from intent import Intent, IntentType
from normalizers import normalize_specialty
from slot_resolver_v2 import resolve_slot_v2


CONFIRM_WORDS = {"yes", "confirm", "book it", "ok"}
RESTART_WORDS = {"restart", "start over", "cancel", "reset"}

# Predict intent based on user text and current state
def predict_intent(user_text, state):
    text = user_text.lower().strip()

    # Restart
    if text in RESTART_WORDS:
        return Intent(IntentType.RESTART)

    # 🔴 CHANGE / SET SPECIALTY (override allowed)
    spec = normalize_specialty(text)
    if spec and spec != state["specialty"]:
        return Intent(
            IntentType.SET_SPECIALTY,
            specialty=spec
        )

    # Confirm booking
    if (
        text in CONFIRM_WORDS
        and state["selected_doctor_id"]
        and state["selected_slot_id"]
        and not state["confirmed"]
    ):
        return Intent(IntentType.CONFIRM_BOOKING)

    # Slot selection
    slot = resolve_slot_v2(user_text, state)
    if slot:
        return Intent(
            IntentType.SELECT_SLOT,
            doctor_id=slot["doctor_id"],
            slot_id=slot["slot_id"]
        )

    # Doctor selection
    if state["available_doctors"] and not state["selected_doctor_id"]:
        for i, d in enumerate(state["available_doctors"], start=1):
            if f"option {i}" in text or d["doctor_name"].lower() in text:
                return Intent(
                    IntentType.SELECT_DOCTOR,
                    doctor_id=d["doctor_id"]
                )

    return Intent(IntentType.UNKNOWN)
