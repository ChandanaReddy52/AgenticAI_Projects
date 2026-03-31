#docbook_stateful_runner.py
from docbook_state import init_booking_state
from selection_parser import resolve_slot_selection, resolve_doctor_selection
from docbook_tools import FindDoctorsTool, CheckAvailabilityTool, BookAppointmentTool
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_tool_calling_agent
from dotenv import load_dotenv
from pathlib import Path
from normalizers import normalize_specialty

load_dotenv()  # Load .env into os.environ
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

tools = [FindDoctorsTool, CheckAvailabilityTool, BookAppointmentTool]

# -----------------------------------
# Resolve prompt path safely
# -----------------------------------
BASE_DIR = Path(__file__).parent
PROMPT_PATH = BASE_DIR / "docbook_agent_prompt_v3.txt"

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
    user_input = input("User: ")
    spec = normalize_specialty(user_input)
    if user_input.lower() in {"exit", "quit"}:
        break
    
    if spec:
        state["specialty"] = spec

    # Slot selection resolution
    if state["available_slots"] and not state["selected_slot_id"]:
        slot_id = resolve_slot_selection(user_input, state["available_slots"])
        if slot_id:
            state["selected_slot_id"] = slot_id
    
    # doc selection
    if state["available_doctors"] and not state["selected_doctor_id"]:
        doc_id = resolve_doctor_selection(user_input, state["available_doctors"])
        if doc_id:
            state["selected_doctor_id"] = doc_id

    if user_input.lower() in {"yes", "confirm"}:
        state["confirmed"] = True

    response = executor.invoke({
        "input": user_input,
        "booking_state": state
    })

    print("\nDocBook:", response["output"], "\n")
