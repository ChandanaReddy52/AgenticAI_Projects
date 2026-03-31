# agent_runner.py
# Stage 1: Single Reactive Agent using LangChain Agent APIs
# Control-flow ownership transferred to the LLM

from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Import existing tools (unchanged)
from tools import document_retriever, answer_generator

# ---------------------------------------------------------
# 1. LLM setup (unchanged model, as agreed)
# ---------------------------------------------------------

llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.0
)

# ---------------------------------------------------------
# 2. Agent system prompt (Single Reactive Agent)
# ---------------------------------------------------------

system_prompt = """
You are a Notion Help Assistant.

Your role is to answer user questions about Notion using official Notion Help documentation.

You are a reactive agent:
- You respond only to user queries.
- You decide whether to use available tools.

You have access to the following tools:
- A document retrieval tool to search Notion Help documentation.
- An answer generation tool that produces grounded answers.

Decision rules:
- First, determine whether the user’s intent is clear and specific.
  - If the intent is unclear or underspecified, ask a single clarification question.
  - Do NOT retrieve documentation yet.

- If the intent is clear, classify the question type:
  - Conceptual or definitional questions may be answered directly.
  - Procedural, step-by-step, account, security, or settings-related questions MUST use the retrieval tool.

Constraints:
- Do NOT answer procedural questions from general knowledge.
- Use retrieval whenever accuracy depends on official documentation.
- If the answer is not found after retrieval, say so clearly.
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

# ---------------------------------------------------------
# 3. Agent creation (THIS is the activation point)
# ---------------------------------------------------------

tools = [document_retriever, answer_generator]

agent = create_openai_functions_agent(
    llm=llm,
    prompt=prompt,
    tools=tools
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True  # IMPORTANT for learning/debugging
)

# ---------------------------------------------------------
# 4. Entry point
# ---------------------------------------------------------

def run_agent(query: str):
    """
    Run the single reactive agent.
    """
    response = agent_executor.invoke({"input": query})
    return response["output"]


if __name__ == "__main__":
    query = "How do I reset my Notion password?"
    output = run_agent(query)
    print("\n=== AGENT RESPONSE ===")
    print(output)
