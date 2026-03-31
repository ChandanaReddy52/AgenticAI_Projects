from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_tool_calling_agent
from dotenv import load_dotenv

load_dotenv()

from docbook_tools import (
    FindDoctorsTool,
    CheckAvailabilityTool,
    BookAppointmentTool
)

# Load prompt
BASE_DIR = Path(__file__).parent
PROMPT_PATH = BASE_DIR / "docbook_agent_prompt.txt"

with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

tools = [
    FindDoctorsTool,
    CheckAvailabilityTool,
    BookAppointmentTool
]

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{input}"),
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

# -----------------------
# Conversation loop
# -----------------------
print("🩺 DocBook Assistant (type 'exit' to quit)\n")

while True:
    user_input = input("User: ")
    if user_input.lower() in {"exit", "quit"}:
        break

    response = executor.invoke({"input": user_input})
    print("\nDocBook:", response["output"], "\n")
