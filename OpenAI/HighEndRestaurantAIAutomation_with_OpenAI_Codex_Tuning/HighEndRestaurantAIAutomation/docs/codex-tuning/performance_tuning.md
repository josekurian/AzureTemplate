# Performance Tuning Guide

**Purpose:** Improves responsiveness, throughput, and reliability across API and Azure AI calls.

## Performance objectives

- Keep guest-facing chat perceived latency low through streaming and incremental UI updates.
- Keep deterministic service calls outside the LLM path whenever possible.
- Parallelize independent calls, such as retrieval and PII detection, when safe.
- Cache stable business data and embeddings.
- Use timeouts, retries, exponential backoff, and circuit breakers.

## Backend tuning

- Use async FastAPI routes for I/O-heavy orchestration.
- Use connection pooling for outbound Azure calls.
- Set per-service timeout budgets: Content Safety 1-2s, Search 1-3s, OpenAI 10-30s depending on response length, Document Intelligence async pollers for long-running jobs.
- Avoid serial calls when independent checks can run concurrently.
- Return early with graceful fallback when optional enrichment fails.

## LLM response tuning

- Limit `max_output_tokens` for routine responses.
- Use small or fast models for classification and routing; reserve larger models for reasoning-heavy tasks.
- Stream long guest-facing responses.
- Use structured outputs to avoid post-processing loops.
- Keep retrieved context compact and relevant.

## Azure AI Search tuning

- Use fields optimized for filtering and faceting.
- Use hybrid retrieval for restaurant knowledge: keyword + vector + semantic ranking.
- Keep chunk size aligned with answer granularity: menu item, policy paragraph, event package section.
- Use metadata filters for document type, effective date, audience, and location.
