# Memory Management Guide

**Purpose:** Defines safe short-term and long-term memory practices for agents and Codex workflows.

## Memory categories

### Ephemeral session state

Use for active conversation details: party size, preferred date, dietary needs, selected menu package, and pending confirmation. Clear after the session or booking workflow.

### Durable business knowledge

Store in Azure AI Search: menu descriptions, wine list, private dining policies, seasonal specials, FAQ, dress code, cancellation policy, and staff training material.

### User preference memory

Only store if the user opts in. Examples: preferred seating style, favorite cuisine, communication language. Do not store sensitive information without a clear business need and consent.

### Prohibited memory

Do not store card numbers, government IDs, sensitive health details, precise location history, or private notes that the user did not authorize.

## Conversation compaction

When a conversation becomes long, compact it into:

- Current goal.
- Confirmed facts.
- Guest constraints.
- Safety constraints.
- Source IDs already used.
- Next action.

## Codex implementation memory

For long coding tasks, Codex should keep a `TASK_NOTES.md` scratchpad in the branch only when requested. It should record decisions, files touched, tests run, unresolved assumptions, and rollback notes.
