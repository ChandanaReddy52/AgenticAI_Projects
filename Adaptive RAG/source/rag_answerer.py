import os
from hybrid_retriever import HybridRetriever
from openai import OpenAI
from dotenv import load_dotenv


# ---------------------------------------------------
# LLM Client
# ---------------------------------------------------

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


# ---------------------------------------------------
# Context Formatting
# ---------------------------------------------------

def format_context(chunks):

    context_parts = []

    for i, c in enumerate(chunks, start=1):

        source = c.get("document_type", "unknown")
        chapter = c.get("chapter", "unknown")

        text = c["text"].strip()

        block = f"""
[Document {i}]
Source: {source}
Section: {chapter}

{text}
"""

        context_parts.append(block)

    return "\n---\n".join(context_parts)


# ---------------------------------------------------
# Prompt Builder
# ---------------------------------------------------

def build_prompt(context, question):

    prompt = f"""
You are a vehicle documentation assistant.

Answer the user's question ONLY using the provided context.

If the answer cannot be found in the context, reply exactly with:
"The provided documents do not contain this information."

Do NOT use outside knowledge.

----------------------
CONTEXT
----------------------

{context}

----------------------
QUESTION
----------------------

{question}

Provide a clear and concise answer.
Cite the document section when possible.
"""

    return prompt


# ---------------------------------------------------
# Answer Verification (NEW)
# ---------------------------------------------------

def verify_answer(context, question, answer):

    verification_prompt = f"""
You are verifying a RAG system answer.

Context:
{context}

Question:
{question}

Answer:
{answer}

Determine whether the answer is fully supported by the context.

Respond with ONLY one word:

YES
or
NO
"""

    response = client.chat.completions.create(

        model="gpt-4o-mini",

        messages=[
            {
                "role": "system",
                "content": "You verify whether answers are grounded in context."
            },
            {
                "role": "user",
                "content": verification_prompt
            }
        ],

        temperature=0
    )

    verdict = response.choices[0].message.content.strip().upper()

    return verdict == "YES"


# ---------------------------------------------------
# RAG Answer Generation
# ---------------------------------------------------

class RAGAnswerer:

    def __init__(self):

        print("Initializing retriever...")
        self.retriever = HybridRetriever()

    def answer(self, retrieval_query, generation_query):

        # ---------------------------------------------------
        # Retrieve context
        # ---------------------------------------------------

        retrieval = self.retriever.retrieve(retrieval_query)

        chunks = retrieval["context"]

        # ---------------------------------------------------
        # DEBUG BLOCK
        # ---------------------------------------------------

        print("\n========== RETRIEVAL DEBUG ==========")
        print("Retrieval Query:\n", retrieval_query)
        print("Generation Query:\n", generation_query)

        for c in chunks:
            print(
                f"Doc: {c.get('document_type')} | "
                f"Section: {c.get('chapter')} | "
                f"Text: {c['text'][:120]}"
            )

        print("=====================================\n")

        # ---------------------------------------------------
        # Safety check
        # ---------------------------------------------------

        if not chunks:
            return "No relevant information found in the documents."

        # ---------------------------------------------------
        # Format context
        # ---------------------------------------------------

        context = format_context(chunks)

        # ---------------------------------------------------
        # Build prompt
        # ---------------------------------------------------

        prompt = build_prompt(context, generation_query)

        # ---------------------------------------------------
        # LLM Generation
        # ---------------------------------------------------

        response = client.chat.completions.create(

            model="gpt-4o-mini",

            messages=[
                {
                    "role": "system",
                    "content": "You answer questions using vehicle documentation."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0
        )

        answer = response.choices[0].message.content.strip()

        # ---------------------------------------------------
        # NEW: ANSWER VERIFICATION STEP
        # ---------------------------------------------------

        is_valid = verify_answer(context, generation_query, answer)

        if not is_valid:

            print("⚠ Answer rejected by verification step")

            return "The provided documents do not contain this information."

        return answer