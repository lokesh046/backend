# chat_service/memory_redis.py

import os
import json
import redis
from typing import Optional
from .financial_state import FinancialState


class RedisMemory:

    def __init__(self):

        # 🔐 Load from Environment Variables
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", 6379))
        self.db = int(os.getenv("REDIS_DB", 0))
        self.ttl_seconds = int(os.getenv("REDIS_TTL", 3600))

        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            decode_responses=True
        )

    # ====================================
    # 🔹 STATE STORAGE
    # ====================================

    def save_state(self, session_id: str, state: FinancialState):
        key = f"finance_state:{session_id}"

        self.client.set(
            key,
            json.dumps(state.to_dict()),
            ex=self.ttl_seconds
        )

    def load_state(self, session_id: str) -> Optional[FinancialState]:
        key = f"finance_state:{session_id}"
        data = self.client.get(key)

        if not data:
            return None

        state_dict = json.loads(data)
        return FinancialState.from_dict(state_dict)

    # ====================================
    # 🔹 CONVERSATION STORAGE
    # ====================================

    def save_conversation(self, session_id: str, message: dict):
        key = f"conversation:{session_id}"

        self.client.lpush(key, json.dumps(message))
        self.client.ltrim(key, 0, 9)
        self.client.expire(key, self.ttl_seconds)

    def get_conversation(self, session_id: str):
        key = f"conversation:{session_id}"
        messages = self.client.lrange(key, 0, -1)
        return [json.loads(m) for m in messages]

    # ====================================
    # 🔹 HEALTH CHECK
    # ====================================

    def ping(self):
        return self.client.ping()