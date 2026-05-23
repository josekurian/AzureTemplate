# Token Optimization Guide

**Purpose:** Reduces context size, token spend, and latency while preserving answer quality.

## Core token rules

- Do not send full documents when a search query can retrieve the relevant chunk.
- Use compact schemas instead of verbose natural language when exchanging data between internal components.
- Summarize conversation history into state rather than appending every message.
- Put static instructions first and variable data last to improve prompt cache reuse.
- Store reusable facts in AI Search, not in prompts.

## Prompt size budgets

- Concierge answer: 300-900 input tokens for simple FAQ, up to 4,000 for complex RAG.
- Menu explanation: top 5-8 relevant menu chunks, not the full menu.
- Private dining: relevant event policy sections only.
- Safety classifier: send the minimum text needed for the safety decision.

## Context compression pattern

```json
{
  "intent": "private_dining_inquiry",
  "guest_constraints": ["12 people", "vegetarian options", "Friday evening"],
  "known_facts": ["No confirmed booking yet"],
  "pending_questions": ["Preferred time", "dietary restrictions"],
  "source_ids": ["private_dining_policy:2026-05"]
}
```

## Anti-patterns

- Including all conversation history in every request.
- Including all search results instead of ranked evidence.
- Duplicating system instructions across nested agent calls.
- Asking the model to parse large JSON when a normal function can do it.
