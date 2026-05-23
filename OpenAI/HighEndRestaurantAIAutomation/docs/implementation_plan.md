# Detailed Implementation Plan

## Phase 1 - Foundation
- Create resource group, managed identities, Key Vault, App Insights, Log Analytics.
- Deploy Azure OpenAI, AI Search, Language, Translator, Speech, Vision, Document Intelligence, Content Safety.
- Assign least-privilege RBAC roles.
- Configure private endpoints where available.

## Phase 2 - Knowledge base and RAG
- Store menu, policy, private dining, allergen, and wine documents in Blob Storage.
- Use embeddings from Azure OpenAI.
- Build AI Search index with keyword, semantic, and vector fields.
- Implement retrieval with citations.

## Phase 3 - Concierge chat
- Pre-screen input with Content Safety.
- Redact PII with Language.
- Retrieve restaurant context with AI Search.
- Generate response with Azure OpenAI.
- Post-screen output with Content Safety.

## Phase 4 - Voice and multilingual support
- Use Speech STT for calls or uploaded audio.
- Use Translator for guest language translation.
- Use Speech TTS for voice replies.

## Phase 5 - Back-office automation
- Use Document Intelligence for supplier invoices and private-event contracts.
- Route high-value or ambiguous invoices to human review.
- Use Language summarization/key phrases for manager reports.

## Phase 6 - Vision and quality assurance
- Use Azure AI Vision for plate image captioning and OCR.
- Use Custom Vision only if prebuilt Vision is insufficient for restaurant-specific plating classes.
- Track model confidence and human review rates.

## Phase 7 - Responsible AI and operations
- Enable Content Safety thresholds and blocklists.
- Configure prompt shields for user and document attacks.
- Create KQL dashboards for latency, errors, tokens, throttling, and safety blocks.
- Add blue/green deployment, rollback, and model version pinning.
