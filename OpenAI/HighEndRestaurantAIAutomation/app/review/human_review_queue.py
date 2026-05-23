from __future__ import annotations

from copy import deepcopy
from uuid import uuid4


class HumanReviewQueue:
    def __init__(self) -> None:
        self._items: dict[str, dict] = {}

    def create(
        self,
        *,
        source: str,
        document_type: str,
        confidence: float,
        reason: str,
        payload: dict,
    ) -> dict:
        review_id = f"review-{uuid4()}"
        item = {
            "review_id": review_id,
            "status": "pending",
            "source": source,
            "document_type": document_type,
            "confidence": confidence,
            "reason": reason,
            "payload": deepcopy(payload),
            "corrections": {},
            "audit_log": [{"action": "created", "reason": reason}],
        }
        self._items[review_id] = item
        return deepcopy(item)

    def list(self, status: str | None = None) -> list[dict]:
        items = list(self._items.values())
        if status:
            items = [item for item in items if item["status"] == status]
        return [deepcopy(item) for item in items]

    def get(self, review_id: str) -> dict | None:
        item = self._items.get(review_id)
        return deepcopy(item) if item else None

    def approve(self, review_id: str, *, actor: str, notes: str | None = None) -> dict:
        return self._update_status(review_id, "approved", actor=actor, notes=notes)

    def reject(self, review_id: str, *, actor: str, notes: str | None = None) -> dict:
        return self._update_status(review_id, "rejected", actor=actor, notes=notes)

    def correct(self, review_id: str, *, actor: str, corrections: dict, notes: str | None = None) -> dict:
        item = self._items[review_id]
        item["status"] = "corrected"
        item["corrections"] = deepcopy(corrections)
        item["audit_log"].append({"action": "corrected", "actor": actor, "notes": notes, "corrections": deepcopy(corrections)})
        return deepcopy(item)

    def _update_status(self, review_id: str, status: str, *, actor: str, notes: str | None = None) -> dict:
        item = self._items[review_id]
        item["status"] = status
        item["audit_log"].append({"action": status, "actor": actor, "notes": notes})
        return deepcopy(item)


human_review_queue = HumanReviewQueue()
