from __future__ import annotations

ROLE_TOOL_PERMISSIONS: dict[str, set[str]] = {
    "guest": {
        "search_knowledge",
        "translate_text",
        "analyze_language",
        "draft_reservation",
        "check_private_dining_policy",
        "summarize_contract",
        "review_safety",
        "recommend_wine_pairing",
    },
    "staff": {
        "search_knowledge",
        "translate_text",
        "analyze_language",
        "draft_reservation",
        "check_private_dining_policy",
        "summarize_contract",
        "review_safety",
        "recommend_wine_pairing",
        "create_manager_packet",
    },
    "manager": {
        "search_knowledge",
        "translate_text",
        "analyze_language",
        "draft_reservation",
        "check_private_dining_policy",
        "summarize_contract",
        "review_safety",
        "recommend_wine_pairing",
        "create_manager_packet",
        "record_approval",
    },
}


def can_use_tool(actor_role: str, tool_name: str) -> bool:
    return tool_name in ROLE_TOOL_PERMISSIONS.get(actor_role, set())


def needs_manager_approval(intent: str, party_size: int | None = None, dietary_notes: str | None = None) -> bool:
    return (
        intent in {"private_dining", "private_dining_inquiry"}
        or (party_size is not None and party_size >= 8)
        or bool(dietary_notes)
    )


def contains_restricted_claim(text: str) -> bool:
    lowered = text.lower()
    return "guarantee allergen-free" in lowered or "confirmed reservation" in lowered
