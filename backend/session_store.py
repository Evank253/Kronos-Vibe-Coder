import os
import json
import uuid
from typing import Dict, Any, Optional

try:
    import redis
except Exception:
    redis = None

REDIS_URL = os.getenv("REDIS_URL")


class RedisSessionStore:
    def __init__(self, url: Optional[str] = None):
        if redis is None:
            raise RuntimeError("redis package not installed")
        self.url = url or REDIS_URL or "redis://localhost:6379/0"
        self.client = redis.from_url(self.url)

    def get(self, session_id: str) -> Dict[str, Any]:
        raw = self.client.get(session_id)
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def set(self, session_id: str, data: Dict[str, Any]):
        self.client.set(session_id, json.dumps(data), ex=60 * 60 * 24)

    def new_session(self) -> str:
        session_id = str(uuid.uuid4())
        self.set(session_id, {})
        return session_id

    def delete(self, session_id: str):
        self.client.delete(session_id)
