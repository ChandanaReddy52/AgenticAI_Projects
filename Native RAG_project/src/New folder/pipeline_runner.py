# pipeline_runner.py — Tool-based RAG execution
# Orchestrates the retrieval and answer generation tools
# Deterministic RAG execution using LangChain tools (no agent yet)

from tools import document_retriever, answer_generator
from memory import load_global_memory, retrieve_contextual_memory


def format_context(chunks: list[dict]) -> str:
    """
    Convert retrieved chunks into a readable context block
    for the answer generator.
    """
    return "\n\n".join(
        f"Chunk {c['rank']}:\n{c['text']}" for c in chunks
    )


def build_memory_instructions(query: str) -> str:
    """
    Retrieve and format memory instructions (global + contextual).
    """
    global_memory = load_global_memory()
    contextual_memory = retrieve_contextual_memory(query)

    memory_instructions = ""

    if global_memory:
        memory_instructions += "Global behavior rules:\n"
        memory_instructions += "\n".join(f"- {m}" for m in global_memory)

    if contextual_memory:
        memory_instructions += "\n\nContextual preferences:\n"
        memory_instructions += "\n".join(f"- {m}" for m in contextual_memory)

    return memory_instructions.strip()


def run_pipeline(query: str):
    """
    End-to-end RAG execution using tools.
    """

    print("\n=== USER QUERY ===")
    print(query)

    # 1️⃣ Retrieve relevant documents (tool call)
    chunks = document_retriever.invoke({"query": query})

    print("\n=== RETRIEVED CHUNKS ===")
    for c in chunks:
        print(f"Rank {c['rank']} | Score {c['score']:.4f}")
        print(c["text"][:300], "\n")

    # 2️⃣ Build context + memory
    context = format_context(chunks)
    memory_instructions = build_memory_instructions(query)

    # 3️⃣ Generate grounded answer (tool call)
    result = answer_generator.invoke({
        "question": query,
        "context": context,
        "memory_instructions": memory_instructions
    })

    print("\n=== FINAL ANSWER ===")
    print(result.answer)

    print("\n=== SOURCES ===")
    print(result.source_doc_ids)

    print("\n=== CONFIDENCE ===")
    print(result.confidence)


if __name__ == "__main__":
    query = "How do I reset my Notion password?"
    run_pipeline(query)
