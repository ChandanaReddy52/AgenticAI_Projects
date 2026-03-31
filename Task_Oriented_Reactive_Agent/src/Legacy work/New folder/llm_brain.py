from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

SYSTEM_PROMPT = """
You are DocBook, a doctor appointment booking assistant.

Rules:
- You MUST describe ONLY what exists in the state
- You MUST ask for the NEXT missing input
- You MUST NOT invent doctors, slots, or specialties
- You MUST NOT say "checking", "loading", or similar
- If no slots available for Dr. X. You may say to choose another doctor or change specialty.
- Be concise and clear
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "Booking state:\n{state}")
])

def llm_brain(_, state: dict, mode: str):
    response = llm.invoke(prompt.format(state=state))
    return None, response.content.strip()
