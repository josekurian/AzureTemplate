# RAG Optimization Guide

**Purpose:** Improves retrieval quality, groundedness, freshness, and citation reliability for restaurant knowledge and similar business corpora.

## Default RAG architecture

```yaml
rag_defaults:
  embeddings_model: text-embedding-3-large
  retrieval_style: hybrid
  initial_candidate_count: 10_to_30
  final_chunk_count_to_model: 4_to_8
  stale_doc_filtering: enabled
  citation_required: true
```

## Chunking strategy

Chunk by semantic unit:

- menu item
- policy paragraph
- FAQ answer
- event package section
- wine note

Recommended starting size:

- `150` to `500` tokens per chunk

Starting overlap:

- `20` to `60` tokens when paragraphs depend on nearby context

## Metadata defaults

```json
{
  "document_type": "policy",
  "audience": "guest",
  "effective_date": "2026-01-15",
  "location": "main_dining_room",
  "confidentiality": "public",
  "source_id": "cancel_policy_v4_s2"
}
```

## Retrieval strategy

- use keyword plus vector retrieval
- apply metadata filters before final ranking
- re-rank semantically if available
- trim down to the strongest evidence before generation

## Grounded generation rules

- cite source IDs inline or in a structured field
- distinguish facts from suggestions
- refuse unsupported claims
- ask a follow-up if a needed field is missing

## Freshness handling

Prioritize:

- current menus over archived menus
- current private dining packages over retired ones
- current seasonal specials over generic examples

Store:

- effective date
- expiration date when available
- version number
- source system or owner

## Advanced suggestions

- keep chunk IDs stable across re-indexes if content is unchanged
- add document titles and section headers into chunk text
- maintain a small labeled retrieval eval set
- test adversarial or prompt-injection-like text in documents

## Multimodal note

If a document includes images, tables, or scans that contain meaning not preserved in plain extraction, mark those chunks for image-aware fallback review rather than treating all OCR text as sufficient.

## Anti-patterns

- indexing giant pages as single chunks
- returning many marginally relevant chunks to the model
- mixing confidential and public docs without metadata separation
- not tracking effective dates
