# Cost Optimization Guide

**Purpose:** Controls spend across model tokens, search, speech, document processing, observability, and Codex usage without degrading important quality.

## Default cost strategy

```yaml
cost_defaults:
  use_deterministic_services_first: true
  output_verbosity: medium_or_low
  max_output_tokens_cap: required
  retrieval_chunk_limit: 4_to_8
  cache_stable_prefixes: true
  eval_cost_budget_required: true
```

## First decision: does this need an LLM?

Use a deterministic or specialized service first when the task is:

- translation
- OCR
- form extraction
- language detection
- named entity extraction
- moderation
- exact document lookup

Use an LLM when the task requires:

- synthesis across sources
- nuanced natural-language generation
- reasoning over ambiguous inputs
- tool selection or orchestrated workflows

## Default model cost ladder

| Task type | Default model choice | Why |
| --- | --- | --- |
| routing, intent, light classification | fast/mini model | low cost, adequate quality |
| standard business answers | `gpt-5.5` | best general quality |
| structured extraction when deterministic service is not enough | fast/mini or standard model with schema | avoid overusing premium reasoning |
| deep analysis or complex review | `gpt-5.5` high reasoning only when justified | expensive, reserve for real need |

## Practical default budgets

```yaml
budget_examples:
  simple_faq_input_tokens: 300_to_900
  simple_faq_output_tokens: 80_to_250
  rag_answer_input_tokens: 1200_to_4000
  routing_output_tokens: 20_to_80
  eval_sample_batch_size: 25_to_100
```

These are starting points, not hard caps. Tune them with evals.

## Cost reduction levers

### Prompt and context

- move stable instructions first for prompt caching
- summarize history instead of replaying it
- trim retrieval to strongest evidence only
- avoid duplicating instructions across nested agent calls

### Models

- lower reasoning effort before changing core prompts
- use lower verbosity for routine responses
- reserve large reasoning budgets for complex tasks only

### Tooling

- call safety checks before expensive generation when blocking is likely
- avoid calling multiple tools that return overlapping data
- use tool search or smaller tool sets to reduce context load

### Batch and async

- use asynchronous processing for back-office jobs
- group offline enrichment or eval runs into batches
- separate guest-facing latency budgets from offline processing budgets

## Restaurant-specific examples

- Use Translator for language conversion, not a premium reasoning model.
- Use Document Intelligence for invoices and forms, not prompt-only parsing.
- Use retrieval for policies instead of pasting policy books into prompts.
- Cache menu and event reference data where freshness requirements allow it.

## What to log for cost control

- model and deployment
- input tokens
- cached tokens
- output tokens
- reasoning effort
- tool count
- retrieval chunk count
- search unit usage
- document page count
- speech minutes

## Alerts to configure

- daily token spend exceeds budget
- cached token rate drops materially
- sudden output token growth
- 429 rate spike
- search or document transaction spike

## Anti-patterns

- Using one premium model for every stage
- Letting outputs grow without word or token budgets
- Paying to re-send the same static prefix in many uncached forms
- Running evals without cost baselines
