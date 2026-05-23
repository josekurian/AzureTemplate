# Prompt Caching and Cache-Aware Prompt Design

**Purpose:** Documents cache-friendly prompt structure and measurement for OpenAI Responses API, Azure OpenAI patterns, and agent workflows.

## Core rule

Keep stable content at the beginning of the request and volatile content at the end.

This aligns with current OpenAI guidance for GPT-5.x and prompt caching.

## Default cache-aware layout

1. role and policy instructions
2. output schema
3. tool descriptions
4. reusable examples
5. compact task state
6. retrieved context
7. current user input

## Example default template

```text
SYSTEM:
You are the AI concierge for a high-end restaurant.
Follow policy. Do not invent reservations, prices, or allergen guarantees.

OUTPUT SCHEMA:
{stable_json_schema_here}

TOOLS:
{stable_tool_descriptions_here}

EXAMPLES:
{stable_examples_here}

STATE:
{compact_state_here}

RETRIEVED_CONTEXT:
{dynamic_chunks_here}

USER:
{dynamic_user_input_here}
```

## Default request settings

```yaml
cache_defaults:
  prompt_cache_key: stable_feature_key
  stable_prefix_required: true
  random_example_rotation: disabled
  timestamps_in_prefix: disabled
```

### Example `prompt_cache_key`

`restaurant-concierge-faq-v3`

Why:

- stable across similar requests
- tied to one feature and prompt version
- easy to measure hit rate

## What should stay stable

- system instructions
- output schema
- tool descriptions
- brand and refusal rules
- few-shot examples

## What should stay late and dynamic

- user message
- retrieved chunks
- tool results
- current session specifics
- request-specific dates if needed

## What to measure

Track:

- input tokens
- cached tokens
- output tokens
- latency
- model
- route or feature
- prompt version

OpenAI currently recommends tracking cached-token usage through response usage details.

## Tradeoff with context engineering

Prompt caching and context compaction are partly in tension:

- caching prefers stable repeated prefixes
- context engineering prefers changing the input to only what matters now

Use evals to decide the right balance, not guesswork.

## Common mistakes

- putting timestamps before stable instructions
- changing tool order every request
- rotating examples randomly
- inlining user-specific data too early
- rewriting the whole system prompt for every call
