from __future__ import annotations

from app.agents.base_agent import AgentContext, AgentResult, BaseAgent
from app.orchestrators.restaurant_concierge import RestaurantConcierge
from app.schemas import ChatRequest


class ConciergeAgent(BaseAgent):
    name = "concierge_agent"

    def __init__(self, tool_registry) -> None:
        super().__init__(tool_registry)
        self.concierge = RestaurantConcierge()

    async def run(self, context: AgentContext) -> AgentResult:
        self_result = await self.concierge.chat(
            ChatRequest(
                message=context.message,
                guest_id=context.guest_id,
                language=context.language,
                channel=context.metadata.get("channel", "web"),
                response_language=context.metadata.get("response_language"),
            )
        )
        result = AgentResult(
            agent_name=self.name,
            answer=self_result.answer,
            safety_decision=self_result.safety_decision,
            sources=self_result.sources,
            data={
                "detected_intent": self_result.detected_intent,
                "sentiment": self_result.sentiment,
                "key_phrases": self_result.key_phrases,
            },
        )
        result.steps.append(self.step("concierge_response", "completed", {"intent": self_result.detected_intent}))
        return result
