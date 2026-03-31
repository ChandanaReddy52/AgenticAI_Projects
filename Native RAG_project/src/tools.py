# tools.py - agent-ready orchestration code for retriever and answer generator tools
# LangChain tools (retriever, answer generator)
from pydantic.v1 import BaseModel, Field


#------------------------------------------LLM-facing contracts--------------------------------#
# Define input schema for the retriever tool
class RetrieverInput(BaseModel):
    query: str = Field(
        description="User query used to retrieve relevant knowledge chunks"
    )

# Define input schema for the answer generator tool
class AnswerGeneratorInput(BaseModel):
    question: str = Field(
        description="The original user question"
    )
    context: str = Field(
        description="Retrieved context to answer the question"
    )
    memory_instructions: str = Field(
        description="Behavior rules and preferences from agent memory"
    )

# Define output schema for the answer generator tool
class AnswerGeneratorOutput(BaseModel):
    answer: str
    source_doc_ids: list[str]
    confidence: str

#--------------------------------Retriever tool------------------------------------------------#

from langchain_core.tools import tool
from retrieval import retrieve_chunks

@tool(args_schema=RetrieverInput)
def document_retriever(query: str):
    """
    Search the internal knowledge base for documents relevant to a user question.
    Returns relevant text chunks with metadata.
    Do NOT use this tool to answer the question directly.
    """
    return retrieve_chunks(query)

#--------------------------------Answer generator tool----------------------------------------------#
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI

# Define LLM and output parser for answer generation
llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.0
)

parser = PydanticOutputParser(
    pydantic_object=AnswerGeneratorOutput
)

@tool(args_schema=AnswerGeneratorInput)
def answer_generator(question: str, context: str, memory_instructions: str):
    """
    Generate a final grounded answer using the retrieved context only.
    If the answer is not present in the context, say you do not have enough information.
    Return a structured response with answer text, source document IDs, and confidence.
    """

    prompt = f"""
    You are a technical documentation assistant.

    MANDATORY BEHAVIOR RULES (must always be followed):
    {memory_instructions if memory_instructions else "None"}

    TASK INSTRUCTIONS:
    - Answer the question using ONLY the information provided in the context.
    - Do NOT use prior knowledge.
    - If the answer is not present in the context, say:
    "I don't have enough information to answer this."

    Context:
    {context}

    Question:
    {question}

    Return your response in the following JSON format:
    {parser.get_format_instructions()}
    """.strip()

    response = llm.invoke(prompt)
    parsed_output = parser.parse(response.content)

    return parsed_output
