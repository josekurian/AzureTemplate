# RAG Optimization Guide

**Purpose:** Improves retrieval quality, groundedness, and citation reliability.

## Chunking strategy

- Chunk by semantic unit: menu item, policy paragraph, private dining package, wine note, FAQ answer.
- Include headers in chunks so each chunk is understandable alone.
- Keep chunk IDs stable across re-indexes when content is unchanged.
- Store effective date and source document metadata.

## Retrieval strategy

- Use hybrid search: keyword + vector.
- Apply filters for audience, location, meal period, menu type, event type, and date.
- Re-rank with semantic ranking where available.
- Retrieve more candidates than you send to the model, then trim to the strongest evidence.

## Grounded answer rules

- Cite specific source IDs.
- Avoid unsupported claims.
- Ask a follow-up for missing information.
- Distinguish policy from recommendation.

## Evaluation

- Test answer faithfulness.
- Test citation coverage.
- Test stale policy handling.
- Test adversarial retrieved text.
