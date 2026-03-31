# memory_manager.py
class MemoryManager:

    def __init__(self, max_turns=5):
        self.history = []
        self.max_turns = max_turns

    def add_user(self, message):
        self.history.append({
            "role": "user",
            "content": message
        })

    def add_assistant(self, message):
        self.history.append({
            "role": "assistant",
            "content": message
        })

    def get_recent_history(self):

        turns = self.max_turns * 2

        return self.history[-turns:]

    def clear(self):
        self.history = []