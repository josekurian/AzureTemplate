# Tools, Function Calling, MCP, and Connector Guide

**Purpose:** Defines safe tool usage patterns for agents and future MCP integrations.

## Tool design principles

- Use tools for authoritative actions: booking lookup, reservation creation, menu inventory, CRM updates, and payment handoff.
- The model proposes tool calls; application code validates authorization, parameters, and business rules.
- Treat tool results as data, not instructions.
- Return structured tool errors that the model can explain safely.

## Function calling schema rules

- Use strict JSON schemas.
- Keep parameter names business-oriented and stable.
- Validate enumerations such as seating area, meal period, diet category, and reservation status.
- Do not expose internal IDs unless required.

## MCP readiness

- Keep tools small and permission-scoped.
- Separate read tools from write tools.
- Require approval for destructive actions.
- Log every tool call with correlation ID, actor, request, result, and latency.

## Restaurant tool candidates

- `search_menu_items`
- `check_private_dining_policy`
- `lookup_reservation_availability`
- `create_reservation_draft`
- `send_guest_followup_email`
- `escalate_to_human_host`
