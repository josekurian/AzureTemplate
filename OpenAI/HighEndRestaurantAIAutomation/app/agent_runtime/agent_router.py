from __future__ import annotations

from app.agent_runtime.trace_context import add_event


class AgentRouter:
    def route(self, message: str, detected_intent: str | None = None) -> str:
        lowered = message.lower()
        if detected_intent == "make_reservation" or "reservation" in lowered or "table" in lowered:
            choice = "reservation_agent"
        elif "private dining" in lowered or "event" in lowered or "banquet" in lowered:
            choice = "private_dining_agent"
        elif "wine" in lowered or "pairing" in lowered or "sommelier" in lowered:
            choice = "sommelier_agent"
        elif "allergy" in lowered or "vegan" in lowered or "menu" in lowered:
            choice = "menu_allergy_agent"
        elif "contract" in lowered or "invoice" in lowered or "document" in lowered:
            choice = "document_agent"
        else:
            choice = "concierge_agent"
        add_event("agent_router", "selected_agent", {"selected_agent": choice, "detected_intent": detected_intent})
        return choice
