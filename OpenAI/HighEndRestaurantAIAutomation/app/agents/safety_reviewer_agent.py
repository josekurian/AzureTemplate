from __future__ import annotations

from app.agents.base_agent import AgentContext, AgentResult, BaseAgent


class SafetyReviewerAgent(BaseAgent):
    name = "safety_reviewer_agent"

    async def run(self, context: AgentContext) -> AgentResult:
        tool_call = await self.call_tool(context, "review_safety", {"text": context.message})
        decision = tool_call.result.get("decision", "allow")
        answer = (
            "Safety review passed." if decision == "allow" else "Safety review blocked the response and requires escalation."
        )
        result = AgentResult(
            agent_name=self.name,
            answer=answer,
            safety_decision=decision,
            tool_calls=[tool_call],
            data=tool_call.result,
        )
        result.steps.append(self.step("safety_review", "completed", {"decision": decision}))
        return result
