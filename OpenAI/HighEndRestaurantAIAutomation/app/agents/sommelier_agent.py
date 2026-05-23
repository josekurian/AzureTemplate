from __future__ import annotations

from app.agents.base_agent import AgentContext, AgentResult, BaseAgent


class SommelierAgent(BaseAgent):
    name = "sommelier_agent"

    async def run(self, context: AgentContext) -> AgentResult:
        tool_call = await self.call_tool(
            context,
            "recommend_wine_pairing",
            {
                "preference": context.metadata.get("preference") or "balanced pairing",
                "dish": context.metadata.get("dish") or "chef's tasting menu",
            },
        )
        result = AgentResult(
            agent_name=self.name,
            answer=tool_call.result["recommendation"],
            sources=tool_call.result.get("sources", []),
            tool_calls=[tool_call],
        )
        result.steps.append(self.step("wine_pairing", "completed"))
        return result
