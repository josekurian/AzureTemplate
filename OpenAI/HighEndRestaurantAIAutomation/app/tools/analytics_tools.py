from __future__ import annotations

from pydantic import BaseModel


class RecordApprovalInput(BaseModel):
    approval_id: str
    decision: str
    actor: str


async def record_approval_tool(data: RecordApprovalInput) -> dict:
    return {
        "approval_id": data.approval_id,
        "decision": data.decision,
        "actor": data.actor,
        "recorded": True,
    }
