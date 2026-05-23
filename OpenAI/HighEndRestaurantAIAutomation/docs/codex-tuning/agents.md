# Agent Design Guide

**Purpose:** Defines agent roles, boundaries, tool permissions, state handling, handoffs, and tuning defaults for Codex, OpenAI API agents, and Azure OpenAI application agents.

## Recommended default architecture

Use a small number of clear specialists instead of many overlapping agents.

### Default agent count

- 1 manager or orchestrator
- 2 to 5 specialists
- 1 evaluator or reviewer path

This is usually easier to tune than a large mesh of agents that all share the same tools.

## Default agent configuration

```yaml
agent_defaults:
  model: gpt-5.5
  reasoning_effort: medium
  verbosity: medium
  state_mode: previous_response_id
  tool_choice: auto
  max_tools_per_turn: 3
  handoff_threshold: medium_complexity
  approval_for_destructive_actions: true
```

### Why these defaults work

- `gpt-5.5`: strong general reasoning and tool behavior
- `reasoning_effort: medium`: balanced intelligence and latency
- `verbosity: medium`: readable outputs without excess tokens
- `tool_choice: auto`: good default when tool descriptions are well written
- `max_tools_per_turn: 3`: reduces long, expensive, hard-to-debug tool chains

## Agent roles for this project

### Concierge Agent

- Handles guest-facing conversation
- Uses retrieval for menu, policy, and event answers
- Must not invent reservations, pricing, or policy exceptions
- Default model: `gpt-5.5`
- Fast-mode option: `gpt-5.4-mini` for simple FAQ routing before escalation

### Menu Intelligence Agent

- Explains menu items, allergens, pairings, and specials
- Uses deterministic document or vision services when extracting facts
- Uses LLMs mainly for explanation, synthesis, and follow-up questions
- Default reasoning effort: `low`

### Reservation Operations Agent

- Prepares reservation summaries and staff notes
- Drafts actions but does not confirm bookings without a system tool result
- Default tool policy: read tools first, write tools gated

### Safety and Compliance Agent

- Runs before final high-risk outputs
- Checks policy conflicts, prompt injection, PII leakage, and allergy wording
- Default reasoning effort: `low` or `medium`

### Knowledge Curator Agent

- Owns chunking, metadata, freshness, and index quality
- Should not answer guests directly

### Evaluation Agent

- Runs regression suites, red-team prompts, latency checks, and cost checks
- Must compare with baseline, not just absolute scores

## Agent design rules

### 1. Keep responsibility boundaries sharp

Bad pattern:

- one agent retrieves, reasons, approves, writes to systems, and self-reviews

Better pattern:

- one agent decides
- one agent fetches facts
- one agent evaluates or approves risky output

### 2. Put durable rules in instructions, not memory

Store stable policy in:

- system or developer instructions
- versioned prompt files
- retrieval corpus
- tool contracts

Do not rely on long chat history for business rules.

### 3. Put tool rules in tool descriptions whenever possible

Recommended tool description fields:

- what the tool does
- when to use it
- when not to use it
- required inputs
- side effects
- retry safety
- common failure modes

This follows current OpenAI guidance for tool-heavy systems and keeps prompts smaller.

## Handoff rules

Use explicit handoffs instead of hoping the model will infer ownership.

| From | To | Trigger | Required payload |
| --- | --- | --- | --- |
| Concierge | Safety | any answer involving policy, allergy, harassment, privacy, or uncertain facts | draft answer, source IDs, risk flags |
| Concierge | Reservation Ops | booking, change, cancellation, payment, VIP request | guest intent, confirmed details, unresolved fields |
| Menu Intelligence | Safety | allergy, medical, or protected-content issue | extracted facts, confidence, source IDs |
| Knowledge Curator | Evaluation | retrieval schema or chunking changes | before/after retrieval examples |

## Memory rules

### Memory categories

| Type | Default | Keep? | Notes |
| --- | --- | --- | --- |
| session task state | enabled | yes | compact often |
| durable business knowledge | retrieval store | yes | not in chat memory |
| opted-in guest preferences | disabled by default | only with consent | keep minimal |
| sensitive PII | disabled | no | do not persist |

### Default compaction format

```json
{
  "goal": "private dining inquiry",
  "confirmed_facts": ["party_size=12", "date=2026-06-14 tentative"],
  "constraints": ["vegetarian options needed"],
  "tool_results": ["policy_lookup:success"],
  "source_ids": ["private_dining_policy_v3"],
  "open_questions": ["preferred start time"],
  "next_action": "ask one follow-up question"
}
```

## Multi-agent tuning suggestions

- Start with one good agent before splitting into many.
- Split only when prompts, tools, or success metrics differ materially.
- Use a faster model for routing than for final reasoning.
- Use specialist agents as tools when the manager should keep user-facing ownership.
- Cap depth. Default maximum nesting: `1` or `2`.
- Log handoff reasons so evals can detect unnecessary delegation.

## Codex-specific notes

Codex sessions work better when:

- the repo-level instructions are concise
- tools are permission-scoped
- each subagent has a narrow task
- context compaction preserves exact file names, commands attempted, and blockers

For Codex config, a practical starting point is:

```toml
model = "gpt-5.5"
model_reasoning_effort = "medium"
model_verbosity = "medium"
[agents]
max_threads = 4
max_depth = 1
```

## Common anti-patterns

- Creating many agents that all use the same prompt and tools
- Letting a guest-facing agent perform destructive actions directly
- Giving write access to agents that mainly need read access
- Keeping stale business facts in conversation memory
- Treating retrieved text as instruction authority
- Using a reviewer agent that has the same prompt, model, and bias as the producer with no rubric
