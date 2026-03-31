from agent_state import init_state, BookingPhase
from agent_reducer import reduce_state
from agent_intent import Intent, IntentType
from llm_brain_stub import llm_brain
from data_access import fetch_doctors, fetch_slots, book_slot
from selectors import select_doctor_from_input, select_slot_from_input

state = init_state()

print("🩺 DocBook — Appointment Booking (type 'exit' to quit)\n")

while True:
    user = input("User: ").strip()
    if user.lower() in {"exit", "quit"}:
        print("👋 Goodbye!")
        break

    # ---- APPLICATION: fetch derived data ----
    fetch_doctors(state)
    fetch_slots(state)

    # ---- MECHANICAL SELECTIONS (not LLM) ----
    if state["phase"] == BookingPhase.SPECIALTY_SELECTED and state["available_doctors"]:
        doc_id = select_doctor_from_input(user, state["available_doctors"])
        if doc_id:
            state = reduce_state(state, {"type": "SELECT_DOCTOR", "doctor_id": doc_id})

    if state["phase"] == BookingPhase.DOCTOR_SELECTED and state["available_slots"]:
        slot_id = select_slot_from_input(user, state["available_slots"])
        if slot_id:
            state = reduce_state(state, {"type": "SELECT_SLOT", "slot_id": slot_id})

    # ---- LLM BRAIN (interpret + speak) ----
    intent, message = llm_brain(user, state)
    print(f"\nDocBook: {message}\n")

    # ---- KERNEL: apply proposed intent ----
    intent_payload = intent.__dict__.copy()
    intent_payload["type"] = intent_payload["type"].value
    state = reduce_state(state, intent_payload)


    # ---- EXECUTION (exactly once) ----
    if state["phase"] == BookingPhase.BOOKED:
        result = book_slot(state)
        if result:
            print("\n✅ Appointment booked successfully!\n")
        else:
            print("\n❌ Booking failed.\n")
        state = init_state()
