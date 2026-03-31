from rag_answerer import RAGAnswerer
from memory_manager import MemoryManager
from sentence_transformers import SentenceTransformer
import numpy as np


class ChatController:

    def __init__(self):

        self.rag = RAGAnswerer()
        self.memory = MemoryManager()

        # model for topic similarity
        self.sim_model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )

    # ---------------------------------------------------
    # Detect topic change
    # ---------------------------------------------------

    def is_topic_switch(self, history, query):

        if not history:
            return False

        last_user = None

        for msg in reversed(history):
            if msg["role"] == "user":
                last_user = msg["content"]
                break

        if not last_user:
            return False

        emb = self.sim_model.encode([last_user, query])

        similarity = np.dot(emb[0], emb[1])

        # threshold tuned for QA systems
        return similarity < 0.35

    # ---------------------------------------------------
    # Retrieval query builder
    # ---------------------------------------------------

    def build_retrieval_query(self, history, query):

        if not history:
            return query

        # detect topic change
        if self.is_topic_switch(history, query):

            print("\n🔄 Topic switch detected — resetting memory\n")

            self.memory.clear()

            return query

        # otherwise treat as follow-up
        last_user = None

        for msg in reversed(history):
            if msg["role"] == "user":
                last_user = msg["content"]
                break

        if not last_user:
            return query

        return f"{query} related to {last_user}"

    # ---------------------------------------------------
    # Context builder for LLM
    # ---------------------------------------------------

    def build_contextual_query(self, history, query):

        if not history:
            return query

        last_user = None
        last_answer = None

        for msg in reversed(history):

            if msg["role"] == "assistant" and last_answer is None:
                last_answer = msg["content"]

            if msg["role"] == "user" and last_user is None:
                last_user = msg["content"]

            if last_user and last_answer:
                break

        if last_user and last_answer:

            contextual_query = f"""
Previous question:
{last_user}

Previous answer:
{last_answer}

Follow up question:
{query}
"""

            return contextual_query.strip()

        return query

    # ---------------------------------------------------
    # Main interaction
    # ---------------------------------------------------

    def ask(self, user_query):

        if user_query.lower().strip() in ["hi", "hello", "hey"]:
            return "Hello! 👋 I'm your Hyundai Vehicle Support Assistant. How can I help you with your vehicle today?"

        history = self.memory.get_recent_history()

        retrieval_query = self.build_retrieval_query(
            history,
            user_query
        )

        contextual_query = self.build_contextual_query(
            history,
            retrieval_query
        )

        answer = self.rag.answer(
            retrieval_query,
            contextual_query
        )

        self.memory.add_user(user_query)
        self.memory.add_assistant(answer)

        return answer