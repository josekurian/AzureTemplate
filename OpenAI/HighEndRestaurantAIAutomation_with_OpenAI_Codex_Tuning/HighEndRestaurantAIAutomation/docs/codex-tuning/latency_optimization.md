# Latency Optimization Guide

**Purpose:** Optimizes time-to-first-token and end-to-end response time.

## Latency targets

- Simple FAQ answer: under 2 seconds when cached/retrieved.
- RAG answer: under 5 seconds for normal context.
- Voice turn: prioritize time-to-first-audio over full response completion.
- Back-office document processing: asynchronous completion is acceptable.

## Techniques

- Stream LLM responses for guest-facing chat.
- Start TTS as soon as a safe response segment is available.
- Parallelize retrieval, PII detection, language detection, and safety pre-checks when possible.
- Use prompt caching by stabilizing prompt prefixes.
- Reduce retrieved context size.
- Use smaller/faster models for low-risk intent routing.
- Cache menu, policy, and embedding lookups.

## Fallbacks

- If retrieval is slow, answer with a graceful message and ask to continue after lookup.
- If OpenAI is slow, return deterministic service output when sufficient.
- If optional enrichment fails, continue with core answer and log the degradation.
