class BotAdapter:
    """Create a safe handoff payload for Azure Bot / omnichannel integration."""

    async def build_handoff_payload(
        self,
        conversation_id: str,
        issue_summary: str,
        guest_name: str | None = None,
        priority: str = "normal",
    ) -> dict:
        return {
            "channel": "azure-bot-service",
            "conversation_id": conversation_id,
            "guest_name": guest_name,
            "issue_summary": issue_summary,
            "priority": priority,
            "handoff_required": True,
            "notes": "Business logic stays in the concierge orchestrator; channels should not duplicate policy logic.",
        }
