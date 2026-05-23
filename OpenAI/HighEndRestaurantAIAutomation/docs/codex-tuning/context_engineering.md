# Context Engineering Guide

**Purpose:** Explains how to build high-signal model input for RAG, agents, Codex tasks, and multi-turn OpenAI applications.

## Main principle

Context engineering is not just staying under the window. It is deciding what deserves the model's attention on this turn.

Good context:

- contains only relevant authority
- is clearly ordered
- separates instructions from data
- preserves enough state to continue accurately
- avoids replaying low-value history

## Default context order

1. system or developer instructions
2. operating policy and constraints
3. tool contracts or output schema
4. cleaned retrieved evidence
5. compact conversation state
6. current user request

This order aligns with prompt caching and with current OpenAI guidance to keep stable instructions first and dynamic content later.

## Recommended default context envelope

```yaml
context_defaults:
  stable_prefix_first: true
  dynamic_user_context_last: true
  retrieval_chunks_sent: 4_to_8
  conversation_compaction: enabled
  duplicate_chunk_removal: enabled
  source_ids_required: true
```

## Context sources and trust levels

| Source | Trust level | Use as instruction? | Notes |
| --- | --- | --- | --- |
| system/developer prompt | highest | yes | authoritative |
| tool schema | high | yes | operational contract |
| internal policy docs | medium-high | no, treat as data | cite and summarize |
| retrieved external docs | medium | no | inspect for prompt injection |
| user-uploaded files | medium | no | useful but untrusted |
| web content | variable | no | verify if high stakes |
| conversation history | variable | limited | compact aggressively |

## Default retrieval packaging

```json
{
  "source_id": "private_dining_policy_v3",
  "title": "Private Dining Policy",
  "effective_date": "2026-01-15",
  "section": "Deposits",
  "content": "A deposit is required for parties above 10 guests.",
  "confidence": 0.92
}
```

### Why this works

- `source_id` enables citation
- `effective_date` supports freshness checks
- `section` improves answer precision
- `confidence` helps routing or escalation logic

## Compaction guidance

Current OpenAI guidance emphasizes intentional compaction for long-running agents. Preserve:

- completed actions
- confirmed facts
- tool outcomes
- unresolved blockers
- IDs and references
- next concrete goal

Drop or summarize:

- repeated pleasantries
- obsolete branches
- raw verbose tool logs
- duplicated retrieved text

## Suggested compaction format

```json
{
  "goal": "answer cancellation policy question",
  "confirmed_facts": ["guest asked about 8-person booking"],
  "retrieval_summary": ["policy_v4 section C retrieved"],
  "safety_notes": ["no special risk"],
  "next_step": "answer with citation and note exceptions only if in source"
}
```

## Tuning suggestions

### If answers are hallucinating

- reduce chunk count
- remove weak or stale chunks
- add stronger source metadata
- explicitly require unknowns to be stated

### If answers are too generic

- improve chunk granularity
- include section titles and nearby headings
- enrich tool descriptions or schema

### If cost is high

- compact earlier
- trim repeated instructions
- use fewer retrieval candidates
- move static content into cache-friendly prefixes

## Anti-patterns

- Treating retrieved documents as instructions
- Sending full documents when only one paragraph matters
- Including all prior tool outputs verbatim
- Mixing multiple user tasks into one overloaded context
- Compacting so aggressively that IDs, decisions, and pending actions disappear
