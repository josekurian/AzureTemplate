from __future__ import annotations

from app.agents.base_agent import AgentContext, AgentResult, BaseAgent


class MenuAllergyAgent(BaseAgent):
    name = "menu_allergy_agent"

    async def run(self, context: AgentContext) -> AgentResult:
        tool_call = await self.call_tool(context, "search_knowledge", {"query": context.message})
        text = tool_call.result.get("context", "")
        answer = (
            "Here is the grounded menu and policy guidance I found. For severe allergies, please confirm directly with the restaurant staff before service."
        )
        result = AgentResult(
            agent_name=self.name,
            answer=answer,
            sources=tool_call.result.get("sources", []),
            tool_calls=[tool_call],
            data={"context": text},
        )
        result.steps.append(self.step("menu_lookup", "completed", {"source_count": len(result.sources)}))
        return result
