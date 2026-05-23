# Token Optimization Guide

**Purpose:** Reduces context size, token spend, and latency while preserving answer quality.

## Token defaults

```yaml
token_defaults:
  full_document_in_prompt: false
  compact_conversation_state: true
  stable_prefix_first: true
  retrieval_chunk_limit: 4_to_8
  output_budget_required: true
```

## Core rules

- retrieve only the needed evidence
- summarize history into state
- use compact schemas for machine-to-machine exchange
- avoid duplicating instructions across agents
- keep static instructions cache-friendly

## Practical input budgets

| Workflow | Starting input budget |
| --- | --- |
| simple FAQ | 300 to 900 tokens |
| normal RAG answer | 1200 to 4000 tokens |
| routing or intent classification | 100 to 500 tokens |
| safety classification | minimum needed text only |

## Practical output budgets

| Workflow | Starting output budget |
| --- | --- |
| routing | 20 to 80 tokens |
| FAQ answer | 80 to 250 tokens |
| policy explanation | 120 to 350 tokens |
| internal summary | 100 to 300 tokens |

## Compact state pattern

```json
{
  "intent": "private_dining_inquiry",
  "guest_constraints": ["12 people", "vegetarian options", "Friday evening"],
  "known_facts": ["No confirmed booking yet"],
  "pending_questions": ["Preferred time", "dietary restrictions"],
  "source_ids": ["private_dining_policy:2026-05"]
}
```

## Good compression moves

- replace full chat replay with structured summaries
- replace verbose prose state with small JSON
- remove repeated tool outputs once their key facts are extracted
- normalize repeated policy text into reusable retrieval chunks

## Anti-patterns

- including all history every turn
- pasting all search results into the model
- asking the model to parse large internal blobs that code can process
- carrying long examples that do not improve quality
