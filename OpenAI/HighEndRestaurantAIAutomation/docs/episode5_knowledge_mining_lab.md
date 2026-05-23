# Episode 5 Knowledge Mining Lab

This Episode 5 expansion adds a restaurant-focused knowledge mining layer on top of the existing agentic and multilingual app. The goal is to practice Azure AI Search, Document Intelligence, and Content Understanding patterns in a way that maps directly to AI-102 study topics.

## What is included

- `POST /search/query` for keyword, vector, hybrid, and semantic-style retrieval
- `GET /search/ingest-status` for quick operational visibility
- `POST /document/receipt` for receipt extraction
- `POST /document/layout` for layout analysis
- `POST /document/contract` for custom event contract extraction
- `POST /content-understanding/analyze` for analyzer-driven multimodal review
- `scripts/build_search_index.py` to create the richer index definition
- `scripts/ingest_documents.py` to chunk local docs, generate embeddings, and upload content
- `analyzers/*.json` to model analyzer contracts for menus, contracts, video, audio, and invoices

## Suggested lab flow

1. Keep `MOCK_MODE=true` and validate the endpoints locally first.
2. Run `scripts/build_search_index.py` to write or create the search schema.
3. Upload documents with `scripts/ingest_documents.py`.
4. Test retrieval with a few restaurant-specific queries:
   - "What is the private dining minimum spend?"
   - "Do you support vegan tasting menus?"
   - "Which documents mention shellfish?"
5. Upload a receipt, invoice, or event contract to the document endpoints.
6. Try the content-understanding analyzers with representative file types.

## Retrieval defaults

- Default query mode: `hybrid`
- Default result count: `5`
- Default semantic config: `restaurant-semantic`
- Default vector size: `3072`
- Suggested filters:
  - `document_type=menu`
  - `document_type=policy`
  - `menu_section=pairings`
  - `allergen_tag=vegan`

## Why this matters for AI-102

- Azure AI Search index design and retrieval strategy
- Grounding prompts with citations
- Chunking and embedding ingestion design
- Information extraction from structured and semi-structured documents
- Separating deterministic extraction from generative orchestration
- Operational thinking: ingest status, review thresholds, metadata filters, and analyzer contracts
