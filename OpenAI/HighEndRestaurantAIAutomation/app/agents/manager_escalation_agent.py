from __future__ import annotations

from app.agents.base_agent import AgentContext, AgentResult, BaseAgent


class ManagerEscalationAgent(BaseAgent):
    name = "manager_escalation_agent"

    async def run(self, context: AgentContext) -> AgentResult:
        tool_call = await self.call_tool(
            context,
            "create_manager_packet",
            {
                "conversation_id": context.metadata.get("conversation_id", context.trace_id),
                "summary": context.message,
                "guest_name": context.metadata.get("guest_name"),
                "priority": context.metadata.get("priority", "high"),
            },
        )
        result = AgentResult(
            agent_name=self.name,
            answer="I prepared a manager escalation packet for human review.",
            tool_calls=[tool_call],
            data=tool_call.result,
        )
        result.steps.append(self.step("manager_packet", "completed"))
        return result
