# chat_service/memory.py

from .state import FinancialState

class MemoryManager:

    def __init__(self):
        self.store = {}

    async def get_state(self, session_id: str):

        if session_id not in self.store:
            self.store[session_id] = FinancialState()

        return self.store[session_id]

    async def save_state(self, session_id: str, state):
        self.store[session_id] = state