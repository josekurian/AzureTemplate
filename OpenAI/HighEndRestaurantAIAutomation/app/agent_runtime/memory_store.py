from __future__ import annotations

from typing import Any


class MemoryStore:
    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}

    def get(self, session_id: str | None) -> dict[str, Any]:
        if not session_id:
            return {}
        return self._sessions.get(session_id, {})

    def update(self, session_id: str | None, patch: dict[str, Any]) -> dict[str, Any]:
        if not session_id:
            return patch
        current = self._sessions.get(session_id, {})
        current.update(patch)
        self._sessions[session_id] = current
        return current


memory_store = MemoryStore()
