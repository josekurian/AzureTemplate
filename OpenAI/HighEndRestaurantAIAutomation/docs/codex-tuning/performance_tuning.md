# Performance Tuning Guide

**Purpose:** Improves responsiveness, throughput, and reliability across API, retrieval, and tool orchestration paths.

## Performance defaults

```yaml
performance_defaults:
  async_io: true
  explicit_timeouts: true
  bounded_retries: true
  circuit_breakers: recommended
  connection_pooling: enabled
  parallel_independent_calls: enabled
  streaming: enabled_for_chat
```

## Backend tuning

- Use async routes for I/O-heavy orchestration.
- Reuse client instances and connection pools.
- Keep per-service timeouts explicit.
- Separate guest-facing fast paths from offline enrichment paths.
- Degrade gracefully when optional enrichment fails.

## Suggested service timeout budgets

```yaml
timeout_budgets_seconds:
  content_safety: 1_to_3
  search: 1_to_5
  embeddings: 5_to_10
  openai_generation: 10_to_30
  reservation_lookup_tool: 3_to_8
```

## LLM performance tuning

- lower reasoning before lowering quality-critical context
- use structured outputs to avoid multiple repair loops
- cap answer length explicitly
- stream long answers
- avoid asking the model to parse large internal JSON if code can do it faster

## Retrieval performance tuning

- use filters early
- keep chunk sizes aligned to answer granularity
- store metadata for narrow selection
- keep vector and keyword retrieval balanced

## Throughput tips

- cache stable business data
- precompute embeddings for documents
- separate high-QPS intent routing from low-QPS deep analysis
- use queues for long-running enrichment

## Reliability and degradation

When a component fails:

- fail closed for safety-critical stages
- fail open only for low-risk optional enrichment
- record the degraded path for later analysis

## Anti-patterns

- serializing independent service calls
- retrying everything blindly
- allowing one slow optional dependency to stall the whole response
- reinitializing AI clients on every request
