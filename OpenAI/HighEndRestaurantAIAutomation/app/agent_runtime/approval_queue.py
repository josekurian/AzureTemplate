from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ApprovalQueue:
    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}

    def create(
        self,
        workflow_type: str,
        required_role: str,
        created_by: str,
        summary: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        approval_id = str(uuid4())
        item = {
            "approval_id": approval_id,
            "workflow_type": workflow_type,
            "status": "pending",
            "required_role": required_role,
            "created_by": created_by,
            "summary": summary,
            "payload": payload,
            "created_at": _utc_now(),
            "decision_notes": None,
        }
        self._items[approval_id] = item
        return item

    def list(self) -> list[dict[str, Any]]:
        return list(self._items.values())

    def get(self, approval_id: str) -> dict[str, Any] | None:
        return self._items.get(approval_id)

    def decide(self, approval_id: str, actor: str, decision: str, notes: str | None = None) -> dict[str, Any]:
        item = self._items[approval_id]
        item["status"] = decision
        item["decided_by"] = actor
        item["decision_notes"] = notes
        item["decided_at"] = _utc_now()
        return item


approval_queue = ApprovalQueue()
