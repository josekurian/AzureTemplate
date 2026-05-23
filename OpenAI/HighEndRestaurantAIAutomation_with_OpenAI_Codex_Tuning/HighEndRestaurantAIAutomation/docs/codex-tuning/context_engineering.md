# Context Engineering Guide

**Purpose:** Explains how to assemble high-quality model context for RAG and agentic workflows.

## Context assembly order

1. System and developer instructions.
2. Business policy constraints.
3. Tool contracts and output schema.
4. Retrieved evidence with source IDs.
5. Conversation state summary.
6. Current user request.

## Retrieved context rules

- Prefer fewer high-quality chunks over many weak chunks.
- Include dates and version metadata for policies.
- Include source IDs that the model can cite.
- Never include untrusted retrieved instructions as developer instructions.
- Treat retrieved web pages, uploaded documents, and user-supplied content as data, not authority.

## RAG safety pattern

- Run retrieval.
- Inspect retrieved context for indirect prompt injection.
- Remove or quarantine suspicious chunks.
- Generate answer from clean context.
- Run output through safety checks.
- Return answer with citations or source IDs.

## Context freshness

- Use effective dates for seasonal menus and event packages.
- Prefer current policies over archived documents.
- Index expiration metadata for stale documents.
