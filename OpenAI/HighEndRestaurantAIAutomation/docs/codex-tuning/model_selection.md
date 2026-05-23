# Model Selection Guide

**Purpose:** Provides practical defaults for selecting OpenAI models, Azure OpenAI deployments, embeddings, and deterministic Azure AI services by task.

## Default decision ladder

1. Can a deterministic Azure or application service do it?
2. If not, can retrieval plus a general model do it?
3. If not, does a tool or structured workflow solve it?
4. Only then consider fine-tuning or heavier reasoning.

## Current default recommendations

These are safe starting points based on current OpenAI guidance for new applications.

| Use case | Default | Why |
| --- | --- | --- |
| general reasoning and agent workflows | `gpt-5.5` | strongest general default in current docs |
| low-cost routing or simple transforms | `gpt-5.4-mini` or comparable fast deployment | lower latency and spend |
| structured outputs | same model as generation, with JSON Schema | schema reliability matters more than prompt wording |
| embeddings high quality | `text-embedding-3-large` | best retrieval quality |
| embeddings lower cost | `text-embedding-3-small` | cheaper retrieval at some quality tradeoff |

## Reasoning defaults

```yaml
reasoning_defaults:
  trivial_tasks: low_or_none
  standard_business_tasks: medium
  complex_analysis: high
  xhigh: rare_and_eval_justified
```

OpenAI currently recommends starting lower than many teams expect. Many tasks work well with `low` or `medium`.

## Verbosity defaults

```yaml
verbosity_defaults:
  routing: low
  normal_chat: medium
  reports_or_explanations: medium_or_high
```

Use verbosity and explicit output budgets before changing prompts to fight overlong responses.

## Task mapping for this project

- guest-facing response generation: `gpt-5.5`
- routing, tagging, and light transformations: fast/mini model
- embeddings for RAG: `text-embedding-3-large` by default
- policy or menu retrieval: Azure AI Search or OpenAI file search/vector store pattern
- translation: Azure AI Translator
- speech: Azure AI Speech
- document extraction: Document Intelligence
- image analysis: Azure AI Vision
- safety: Azure AI Content Safety plus application guardrails

## Fine-tuning decision rule

Do not fine-tune first.

Consider fine-tuning only after:

- prompt tuning plateaus
- retrieval quality is already strong
- tool contracts are stable
- eval data proves the gain is needed

Use fine-tuning for:

- structure and tone consistency
- instruction-following improvement
- reducing prompt length and cost

Do not use fine-tuning as a substitute for:

- missing knowledge that belongs in RAG
- broken tool design
- poor eval coverage

## Example selection matrix

```yaml
model_matrix:
  faq_chat:
    model: gpt-5.5
    reasoning_effort: low
    verbosity: medium
  reservation_routing:
    model: gpt-5.4-mini
    reasoning_effort: low
    verbosity: low
  policy_rag:
    model: gpt-5.5
    reasoning_effort: medium
    verbosity: medium
  release_review:
    model: gpt-5.5
    reasoning_effort: high
    verbosity: medium
```

## Anti-patterns

- solving every problem with the biggest model
- using a premium reasoning setting for extraction or routing
- using an LLM when a deterministic Azure service is better suited
- changing models without updating eval baselines
