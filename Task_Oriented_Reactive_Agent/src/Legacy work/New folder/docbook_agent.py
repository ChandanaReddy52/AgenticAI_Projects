from agent_state import init_state, BookingPhase
from agent_reducer import reduce_state
from llm_brain import llm_brain
from data_access import fetch_doctors, fetch_slots, book_slot
from selectors import select_doctor_from_input, select_slot_from_input
from canonicalizers import canonicalize_specialty

state = init_state()

print("🩺 DocBook — Appointment Booking (type 'exit' to quit)\n")

while True:
    user = input("User: ").strip()

    if user.lower() in {"exit", "quit"}:
        print("👋 Goodbye!")
        break

    # --------------------------------------------------
    # 1. SPECIALTY
    # --------------------------------------------------
    if state["phase"] == BookingPhase.START:
        specialty = canonicalize_specialty(user)
        if specialty:
            state = reduce_state(state, {
                "type": "SET_SPECIALTY",
                "specialty": specialty
            })
            fetch_doctors(state)
            _, msg = llm_brain(None, state, mode="narrate")
            print(f"\nDocBook: {msg}\n")
            continue

    # --------------------------------------------------
    # 2. DOCTOR
    # --------------------------------------------------
    if state["phase"] == BookingPhase.SPECIALTY_SELECTED:
        doctor_id = select_doctor_from_input(user, state["available_doctors"])
        if doctor_id:
            state = reduce_state(state, {
                "type": "SELECT_DOCTOR",
                "doctor_id": doctor_id
            })
            fetch_slots(state)
            _, msg = llm_brain(None, state, mode="narrate")
            print(f"\nDocBook: {msg}\n")
            continue

    # --------------------------------------------------
    # 3A. NO SLOTS → ALLOW DOCTOR SWITCH
    # --------------------------------------------------
    if state["phase"] == BookingPhase.DOCTOR_SELECTED and not state["available_slots"]:
        doctor_id = select_doctor_from_input(user, state["available_doctors"])
        if doctor_id and doctor_id != state["doctor_id"]:
            state = reduce_state(state, {
                "type": "SELECT_DOCTOR",
                "doctor_id": doctor_id
            })
            fetch_slots(state)
            _, msg = llm_brain(None, state, mode="narrate")
            print(f"\nDocBook: {msg}\n")
            continue

        print(
            "\nDocBook: No slots are available for this doctor. "
            "You may choose another doctor or change the specialty.\n"
        )
        continue

    # --------------------------------------------------
    # 3B. SLOT SELECTION (THIS WAS MISSING)
    # --------------------------------------------------
    if state["phase"] == BookingPhase.DOCTOR_SELECTED and state["available_slots"]:
        slot_id = select_slot_from_input(user, state["available_slots"])
        if slot_id:
            state = reduce_state(state, {
                "type": "SELECT_SLOT",
                "slot_id": slot_id
            })
            state["phase"] = BookingPhase.AWAITING_PATIENT_NAME
            _, msg = llm_brain(None, state, mode="narrate")
            print(f"\nDocBook: {msg}\n")
            continue

        # user typed something else → show slots again
        _, msg = llm_brain(None, state, mode="narrate")
        print(f"\nDocBook: {msg}\n")
        continue

    # --------------------------------------------------
    # 4. PATIENT NAME → BOOK
    # --------------------------------------------------
    if state["phase"] == BookingPhase.AWAITING_PATIENT_NAME:
        state["patient_name"] = user
        book_slot(state)
        print("\n✅ Appointment booked successfully!\n")
        state = init_state()
        continue

    # --------------------------------------------------
    # FALLBACK NARRATION
    # --------------------------------------------------
    _, msg = llm_brain(None, state, mode="narrate")
    print(f"\nDocBook: {msg}\n")
