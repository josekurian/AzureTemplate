from __future__ import annotations

import re
from typing import Any

from app.agent_runtime.approval_queue import approval_queue
from app.agent_runtime.policies import needs_manager_approval
from app.agent_runtime.trace_context import add_event


class WorkflowEngine:
    def __init__(self, agent_service) -> None:
        self.agent_service = agent_service

    def _party_size(self, message: str) -> int:
        match = re.search(r"\b(\d{1,2})\b", message)
        return int(match.group(1)) if match else 2

    async def run_private_dining(self, payload: dict[str, Any]) -> dict[str, Any]:
        selected_agents = []
        concierge = await self.agent_service.run_agent_chat(
            {
                "message": payload["message"],
                "guest_id": payload.get("guest_id"),
                "language": payload.get("language", "en"),
                "session_id": payload.get("session_id"),
                "actor_role": "guest",
                "channel": "web",
            }
        )
        selected_agents.append(concierge.selected_agent)

        private_context = {
            "message": payload["message"],
            "guest_id": payload.get("guest_id"),
            "language": payload.get("language", "en"),
            "session_id": payload.get("session_id"),
            "actor_role": "guest",
            "channel": "web",
            "force_agent": "private_dining_agent",
            "guest_name": payload.get("guest_name"),
        }
        private_dining = await self.agent_service.run_agent_chat(private_context)
        selected_agents.append(private_dining.selected_agent)

        approval_ids: list[str] = []
        party_size = self._party_size(payload["message"])
        if needs_manager_approval("private_dining", party_size=party_size):
            approval = approval_queue.create(
                workflow_type="private_dining",
                required_role="manager",
                created_by="workflow_engine",
                summary="Manager review required for private dining workflow.",
                payload={
                    "guest_name": payload.get("guest_name"),
                    "party_size": party_size,
                    "message": payload["message"],
                    "trace_id": private_dining.trace_id,
                },
            )
            approval_ids.append(approval["approval_id"])
            add_event("workflow_engine", "approval_created", approval)

        summary = {
            "concierge_answer": concierge.answer,
            "private_dining_answer": private_dining.answer,
            "party_size": party_size,
        }
        final_answer = (
            "Your request has been prepared for private dining review. A manager will verify package details, minimum spend, and next steps before anything is finalized."
            if approval_ids
            else private_dining.answer
        )
        return {
            "workflow_type": "private_dining",
            "trace_id": private_dining.trace_id,
            "status": "awaiting_approval" if approval_ids else "completed",
            "selected_agents": selected_agents,
            "approvals_requested": approval_ids,
            "final_answer": final_answer,
            "summary": summary,
        }
