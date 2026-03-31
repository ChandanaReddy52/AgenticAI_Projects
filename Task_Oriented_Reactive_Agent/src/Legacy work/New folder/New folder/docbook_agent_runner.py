from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_tool_calling_agent
from dotenv import load_dotenv


load_dotenv()  # Load .env into os.environ

from docbook_tools import (
    FindDoctorsTool,
    CheckAvailabilityTool,
    BookAppointmentTool
)

# -----------------------------------
# Resolve prompt path safely
# -----------------------------------
BASE_DIR = Path(__file__).parent
PROMPT_PATH = BASE_DIR / "docbook_agent_prompt.txt"

with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

# -----------------------------------
# LLM + tools
# -----------------------------------
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

tools = [
    FindDoctorsTool,
    CheckAvailabilityTool,
    BookAppointmentTool
]

# system prompt with user input and booking state
prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "User input: {input}\n\nBooking state: {booking_state}"),
    ("placeholder", "{agent_scratchpad}")
])

agent = create_tool_calling_agent(
    llm=llm,
    tools=tools,
    prompt=prompt
)

executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True
)

#executor.invoke({"input": "Book a dermatologist appointment"})