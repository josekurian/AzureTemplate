from __future__ import annotations

import re

from app.agents.base_agent import AgentContext, AgentResult, BaseAgent


class ReservationAgent(BaseAgent):
    name = "reservation_agent"

    def _extract_party_size(self, message: str) -> int:
        match = re.search(r"\b(\d{1,2})\b", message)
        if match:
            return int(match.group(1))
        if "two" in message.lower():
            return 2
        return 2

    async def run(self, context: AgentContext) -> AgentResult:
        party_size = self._extract_party_size(context.message)
        tool_call = await self.call_tool(
            context,
            "draft_reservation",
            {
                "guest_name": context.metadata.get("guest_name", "Guest"),
                "date": context.metadata.get("date", "TBD"),
                "time": context.metadata.get("time", "TBD"),
                "party_size": party_size,
                "dietary_notes": context.metadata.get("dietary_notes"),
                "occasion": context.metadata.get("occasion"),
                "language": context.language,
            },
        )
        answer = (
            "I have prepared a reservation draft. A team member must verify live availability before anything is confirmed."
        )
        result = AgentResult(
            agent_name=self.name,
            answer=answer,
            tool_calls=[tool_call],
            data={"party_size": party_size, "draft": tool_call.result},
        )
        result.steps.append(self.step("draft_reservation", "completed", {"party_size": party_size}))
        return result
