from __future__ import annotations

from app.agents.base_agent import AgentContext, AgentResult, BaseAgent


class DocumentAgent(BaseAgent):
    name = "document_agent"

    async def run(self, context: AgentContext) -> AgentResult:
        tool_call = await self.call_tool(
            context,
            "summarize_contract",
            {"document_text": context.metadata.get("document_text") or context.message},
        )
        result = AgentResult(
            agent_name=self.name,
            answer="I summarized the contract content and flagged it for human review.",
            tool_calls=[tool_call],
            data=tool_call.result,
        )
        result.steps.append(self.step("contract_summary", "completed"))
        return result
