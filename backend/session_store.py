"""Session store – Redis when available, otherwise in-memory."""
from __future__ import annotations

import os
import json
import uuid
from typing import Dict, Any, Optional

try:
    import redis
except Exception:  # pragma: no cover
    redis = None

REDIS_URL = os.getenv("REDIS_URL")


class MemorySessionStore:
    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, Any]] = {}

    def get(self, session_id: str) -> Dict[str, Any]:
        return dict(self._data.get(session_id) or {})

    def set(self, session_id: str, data: Dict[str, Any]) -> None:
        self._data[session_id] = dict(data)

    def new_session(self) -> str:
        session_id = str(uuid.uuid4())
        self.set(session_id, {})
        return session_id

    def delete(self, session_id: str) -> None:
        self._data.pop(session_id, None)


class RedisSessionStore:
    def __init__(self, url: Optional[str] = None) -> None:
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

    def set(self, session_id: str, data: Dict[str, Any]) -> None:
        self.client.set(session_id, json.dumps(data), ex=60 * 60 * 24)

    def new_session(self) -> str:
        session_id = str(uuid.uuid4())
        self.set(session_id, {})
        return session_id

    def delete(self, session_id: str) -> None:
        self.client.delete(session_id)


def get_session_store():
    """Prefer Redis when configured and importable; else memory."""
    if redis is not None and (REDIS_URL or os.getenv("USE_REDIS") == "1"):
        try:
            return RedisSessionStore()
        except Exception:
            pass
    return MemorySessionStore()
