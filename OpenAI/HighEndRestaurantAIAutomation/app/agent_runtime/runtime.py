from __future__ import annotations

from app.agents.base_agent import AgentContext
from app.agents.concierge_agent import ConciergeAgent
from app.agents.document_agent import DocumentAgent
from app.agents.manager_escalation_agent import ManagerEscalationAgent
from app.agents.menu_allergy_agent import MenuAllergyAgent
from app.agents.private_dining_agent import PrivateDiningAgent
from app.agents.reservation_agent import ReservationAgent
from app.agents.safety_reviewer_agent import SafetyReviewerAgent
from app.agents.sommelier_agent import SommelierAgent
from app.agent_runtime.agent_router import AgentRouter
from app.agent_runtime.memory_store import memory_store
from app.agent_runtime.tool_registry import ToolDefinition, ToolRegistry
from app.agent_runtime.trace_context import add_event, finish_trace, set_current_trace, start_trace
from app.schemas import AgentChatResponse
from app.tools.analytics_tools import RecordApprovalInput, record_approval_tool
from app.tools.communication_tools import (
    ManagerPacketInput,
    TranslateTextInput,
    create_manager_packet_tool,
    translate_text_tool,
)
from app.tools.document_tools import ContractSummaryInput, summarize_contract_tool
from app.tools.menu_tools import MenuLookupInput, WinePairingInput, lookup_menu_tool, recommend_wine_pairing_tool
from app.tools.reservation_tools import ReservationDraftInput, draft_reservation_tool
from app.tools.safety_tools import SafetyReviewInput, review_safety_tool
from app.tools.search_tools import (
    PrivateDiningPolicyInput,
    SearchKnowledgeInput,
    private_dining_policy_tool,
    search_knowledge_tool,
)


class AgentRuntime:
    def __init__(self) -> None:
        self.tool_registry = ToolRegistry()
        self._register_tools()
        self.router = AgentRouter()
        self.agents = {
            "concierge_agent": ConciergeAgent(self.tool_registry),
            "reservation_agent": ReservationAgent(self.tool_registry),
            "menu_allergy_agent": MenuAllergyAgent(self.tool_registry),
            "sommelier_agent": SommelierAgent(self.tool_registry),
            "private_dining_agent": PrivateDiningAgent(self.tool_registry),
            "document_agent": DocumentAgent(self.tool_registry),
            "safety_reviewer_agent": SafetyReviewerAgent(self.tool_registry),
            "manager_escalation_agent": ManagerEscalationAgent(self.tool_registry),
        }

    def _register_tools(self) -> None:
        self.tool_registry.register(
            ToolDefinition("search_knowledge", "Search grounded restaurant knowledge.", SearchKnowledgeInput, search_knowledge_tool)
        )
        self.tool_registry.register(
            ToolDefinition("draft_reservation", "Create a reservation draft only.", ReservationDraftInput, draft_reservation_tool)
        )
        self.tool_registry.register(
            ToolDefinition("check_private_dining_policy", "Retrieve private dining policy details.", PrivateDiningPolicyInput, private_dining_policy_tool)
        )
        self.tool_registry.register(
            ToolDefinition("lookup_menu", "Retrieve grounded menu context.", MenuLookupInput, lookup_menu_tool)
        )
        self.tool_registry.register(
            ToolDefinition("recommend_wine_pairing", "Recommend a grounded pairing suggestion.", WinePairingInput, recommend_wine_pairing_tool)
        )
        self.tool_registry.register(
            ToolDefinition("review_safety", "Run safety review and prompt-injection checks.", SafetyReviewInput, review_safety_tool)
        )
        self.tool_registry.register(
            ToolDefinition("summarize_contract", "Summarize private event or contract text.", ContractSummaryInput, summarize_contract_tool)
        )
        self.tool_registry.register(
            ToolDefinition("translate_text", "Translate guest or staff text.", TranslateTextInput, translate_text_tool)
        )
        self.tool_registry.register(
            ToolDefinition("create_manager_packet", "Create a handoff packet for manager review.", ManagerPacketInput, create_manager_packet_tool)
        )
        self.tool_registry.register(
            ToolDefinition("record_approval", "Record an approval decision.", RecordApprovalInput, record_approval_tool)
        )

    async def run_agent_chat(self, payload: dict) -> AgentChatResponse:
        trace_id = start_trace("agent_chat", {"session_id": payload.get("session_id")})
        detected_intent = None
        if "reservation" in payload["message"].lower():
            detected_intent = "make_reservation"
        selected_agent_name = payload.get("force_agent") or self.router.route(payload["message"], detected_intent=detected_intent)
        context = AgentContext(
            session_id=payload.get("session_id"),
            trace_id=trace_id,
            actor_role=payload.get("actor_role", "guest"),
            message=payload["message"],
            language=payload.get("language", "en"),
            guest_id=payload.get("guest_id"),
            metadata={
                "channel": payload.get("channel", "web"),
                "response_language": payload.get("response_language"),
                "guest_name": payload.get("guest_name"),
                "date": payload.get("date"),
                "time": payload.get("time"),
                "dietary_notes": payload.get("dietary_notes"),
                "occasion": payload.get("occasion"),
                "conversation_id": payload.get("conversation_id", trace_id),
                "priority": payload.get("priority", "high"),
                "preference": payload.get("preference"),
                "dish": payload.get("dish"),
                "document_text": payload.get("document_text"),
            },
        )
        set_current_trace(trace_id)
        agent = self.agents[selected_agent_name]
        agent_result = await agent.run(context)
        memory_snapshot = memory_store.update(
            payload.get("session_id"),
            {
                "last_agent": selected_agent_name,
                "last_message": payload["message"],
                "last_answer": agent_result.answer,
            },
        )
        add_event("agent_runtime", "memory_updated", memory_snapshot)
        finish_trace("completed", {"selected_agent": selected_agent_name})
        return AgentChatResponse(
            trace_id=trace_id,
            selected_agent=selected_agent_name,
            answer=agent_result.answer,
            safety_decision=agent_result.safety_decision,
            tool_calls=[
                {
                    "tool_name": call.tool_name,
                    "status": call.status,
                    "actor_role": call.actor_role,
                    "result": call.result,
                }
                for call in agent_result.tool_calls
            ],
            steps=[
                {
                    "agent": step.agent,
                    "action": step.action,
                    "status": step.status,
                    "details": step.details,
                }
                for step in agent_result.steps
            ],
            sources=agent_result.sources,
            approvals_requested=agent_result.approvals_requested,
            memory_snapshot=memory_snapshot,
        )


agent_runtime = AgentRuntime()
