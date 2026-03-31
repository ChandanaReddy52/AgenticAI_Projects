#docbook_stateful_runner.py
from docbook_state import init_booking_state
from docbook_tools import BookAppointmentTool
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_tool_calling_agent
from dotenv import load_dotenv
from pathlib import Path
from normalizers import normalize_specialty
from intent_predictor import predict_intent
from reducer import reduce_state
from state_sync import sync_state_from_agent
from data_store import (
    get_active_doctors_by_specialty,
    get_available_slots_by_doctor_id
)


load_dotenv()  # Load .env into os.environ
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

tools = [BookAppointmentTool]

# -----------------------------------
# Resolve prompt path safely
# -----------------------------------
BASE_DIR = Path(__file__).parent
PROMPT_PATH = BASE_DIR / "docbook_agent_prompt_v4.txt"

with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "User input: {input}\n\nBooking state: {booking_state}"),
    ("placeholder", "{agent_scratchpad}")
])


agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

state = init_booking_state()


print("🩺 DocBook — Appointment Booking (type 'exit' to quit)\n")

while True:
    user_input = input("User: ").strip()

    # 1️⃣ Exit immediately
    if user_input.lower() in {"exit", "quit"}:
        print("👋 Goodbye!")
        break

    # 2️⃣ Predict intent (NO state mutation)
    intent = predict_intent(user_input, state)

    # 3️⃣ Apply intent (ONLY place state mutates)
    state = reduce_state(state, intent)

    # 4️⃣ APPLICATION LAYER DATA FETCH (AUTHORITATIVE)
    # Fetch doctors if needed
    if state["specialty"] and not state["available_doctors"]:
        state["available_doctors"] = get_active_doctors_by_specialty(
            state["specialty"]
        )

    # Fetch slots if doctor selected and slots missing
    if state["selected_doctor_id"] and not state["available_slots"]:
        state["available_slots"] = get_available_slots_by_doctor_id(
            state["selected_doctor_id"]
        )

    # 🔥 Let agent reason + call tools
    response = executor.invoke({
        "input": user_input,
        "booking_state": state
    })

    print("\nDocBook:", response["output"], "\n")

if isinstance(response.get("output"), dict):
    state = sync_state_from_agent(state, response["output"])