from memory import write_memory

"""
write_memory(
    memory_type="preference",
    content="User prefers concise, step-by-step technical explanations.",
    importance="high"
) """

'''
write_memory(
    memory_type="preference",
    content="""Formatting Rules (MANDATORY):
            - Use strictly numbered bullet points.
            - Do not use paragraphs""",
    importance="high"
) '''

# Adding a global preference memory entry to enforce formatting rules without semantic confusion
write_memory(
    memory_type="global_preference",
    content="Use strictly numbered bullet points. Do not use paragraphs.",
    importance="high"
)

# Adding a contextual preference memory entry - enforced by relevance to current queries
write_memory(
    memory_type="contextual_preference",
    content="User prefers concise, step-by-step technical explanations.",
    importance="high"
)
