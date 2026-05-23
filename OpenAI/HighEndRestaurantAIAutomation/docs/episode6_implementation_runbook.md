# Episode 6 Implementation Runbook

This runbook expands the restaurant sample from Episode 5 knowledge mining into a fuller Episode 6 ingestion, extraction, review, and retrieval pipeline.

## What Episode 6 adds

- `app/ingestion/` for chunking, normalization, embeddings, and end-to-end ingestion orchestration
- `app/review/human_review_queue.py` for low-confidence review gates
- `POST /ingestion/jobs` and review endpoints for operational workflows
- `POST /search/query/v2` with facets, richer filters, diagnostics, and zero-result fallback
- `GET /search/query-log` for mock telemetry inspection
- `POST /document/*/v2` and `POST /content-understanding/analyze/v2` for richer grounding and confidence payloads
- infrastructure JSON for search index, skillset, indexer, and content-understanding analyzers

## Acceptance checklist

- Search supports keyword, vector, hybrid, and semantic-style retrieval.
- Search responses include citations, chunk IDs, confidence, and applied-filter diagnostics.
- Ingestion can classify uploads into Document Intelligence or Content Understanding routes.
- Low-confidence extractions enter the review queue instead of publishing directly.
- Approved or corrected content can be audited through the review record.
- Content-understanding analyzers expose schema metadata through the API.
- Tests pass in mock mode for chunking, ingestion, review, search, and extraction.

## Suggested validation flow

1. Upload `menu.pdf` to `POST /ingestion/jobs` and confirm direct indexing.
2. Upload `private_event_contract.pdf` and confirm `review_required`.
3. Query `POST /search/query/v2` for a dining-policy question and verify citations.
4. Inspect `GET /search/query-log` to confirm diagnostics are emitted.
5. List `GET /reviews` and complete a correction flow for a low-confidence document.
