# Memory Management Guide

**Purpose:** Defines safe short-term and long-term memory practices for OpenAI agents, Codex sessions, and application-side state.

## First rule

Not everything should be memory. Separate:

- business knowledge
- transient task state
- opted-in preferences
- prohibited sensitive data

## Default memory policy

```yaml
memory_defaults:
  session_state: enabled
  durable_business_memory: retrieval_store
  opted_in_user_preferences: limited
  external_context_memory_generation: disabled_when_sensitive
  periodic_compaction: enabled
```

## Memory categories

### Ephemeral session state

Use for current-turn and current-workflow facts.

Examples:

- party size
- intended date
- preferred cuisine
- unresolved questions

Default retention:

- clear after session or completed workflow

### Durable business knowledge

Store in retrieval or source systems, not chat memory.

Examples:

- menus
- event packages
- cancellation policy
- dress code
- opening hours

### User preference memory

Store only with clear business need and explicit consent.

Examples:

- preferred language
- seating preference
- favorite wine style

### Prohibited memory

Never store:

- card numbers
- government IDs
- precise health data without strict need and controls
- hidden staff notes not authorized for reuse

## Conversation compaction

Use compaction when:

- conversation history grows large
- prompt caching benefits from a smaller dynamic tail
- the workflow has completed sub-steps that can be summarized

Recommended compaction fields:

- goal
- confirmed facts
- constraints
- relevant source IDs
- tool results
- blockers
- next action

## Codex-specific notes

Current Codex config supports memory features and memory generation controls. A practical user-level starting point is:

```toml
[features]
memories = true

[memories]
generate_memories = true
use_memories = true
disable_on_external_context = true
max_raw_memories_for_consolidation = 256
max_rollout_age_days = 30
min_rollout_idle_hours = 6
min_rate_limit_remaining_percent = 25
```

### Why these values are good defaults

- `disable_on_external_context = true`: safer when prompts rely on web or MCP context
- `256` raw memories: enough history without uncontrolled growth
- `30` days: recent enough for coding patterns and stable preferences
- `6` idle hours: avoids over-eager consolidation

## Anti-patterns

- storing policy in conversational memory instead of retrieval
- keeping raw full transcripts when a compact state is enough
- retaining sensitive details because they might be useful later
- generating memory from noisy external context without review
