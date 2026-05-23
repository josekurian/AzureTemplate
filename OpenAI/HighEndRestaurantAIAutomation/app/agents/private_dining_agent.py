from __future__ import annotations

from app.agents.base_agent import AgentContext, AgentResult, BaseAgent


class PrivateDiningAgent(BaseAgent):
    name = "private_dining_agent"

    async def run(self, context: AgentContext) -> AgentResult:
        tool_call = await self.call_tool(context, "check_private_dining_policy", {"query": context.message})
        answer = (
            "I found the private dining policy details and prepared the event-planning context. A manager review is required before any quote or contract is finalized."
        )
        result = AgentResult(
            agent_name=self.name,
            answer=answer,
            sources=tool_call.result.get("sources", []),
            tool_calls=[tool_call],
            data={"policy_summary": tool_call.result.get("summary", "")},
        )
        result.steps.append(self.step("private_dining_policy", "completed"))
        return result
