# Latency Optimization Guide

**Purpose:** Optimizes time-to-first-token and end-to-end latency for chat, RAG, voice, and tool-based workflows.

## Recommended default targets

```yaml
latency_targets:
  simple_faq_p95_seconds: 2
  rag_answer_p95_seconds: 5
  voice_first_audio_seconds: 1.5_to_3
  offline_document_jobs: async
```

## Most effective levers

1. reduce unnecessary context
2. use the right model size and reasoning effort
3. stream outputs
4. parallelize independent checks
5. improve cache hit rate
6. avoid unnecessary tools

## Default latency settings

```yaml
latency_defaults:
  stream_responses: true
  reasoning_effort_for_normal_chat: low_or_medium
  text_verbosity: medium
  retrieval_chunk_count: 4_to_8
  safety_precheck_parallel: true
  pii_check_parallel: true
```

## OpenAI-specific guidance

Current OpenAI guidance for GPT-5.x favors:

- Responses API for new work
- lower `reasoning.effort` when speed matters more than deep analysis
- `text.verbosity` to control answer length
- prompt caching through stable prefixes

## Parallelization opportunities

Run in parallel when independent:

- retrieval
- language detection
- PII detection
- safety pre-check
- cached business metadata lookup

Do not parallelize when later stages depend directly on earlier outputs.

## Retrieval latency tips

- pre-filter by document type or date before vector ranking
- keep index fields tuned for filters
- avoid returning many weak chunks
- cache common menu and policy lookups

## Voice workflow tips

- optimize time to first audio, not just full answer latency
- start TTS after a safe partial segment if the stack supports it
- keep first sentence short and useful

## Fallback strategy

If a slow dependency exceeds its budget:

- answer from a deterministic or cached source when safe
- ask to continue after lookup if the source is mandatory
- drop optional enrichment and log the degraded path

## Anti-patterns

- using high reasoning for every turn
- returning long paragraphs for trivial requests
- calling tools serially when they do not depend on one another
- sending bloated context that barely changes per request
