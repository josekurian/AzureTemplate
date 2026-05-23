# Model Selection Guide

**Purpose:** Provides rules for selecting models and Azure AI services by task.

## Decision ladder

1. Can a deterministic Azure AI service do it? Use that first.
2. Can retrieval plus a general model do it? Use RAG.
3. Does the task need a custom classifier or extractor? Train or configure the relevant Azure AI service.
4. Does the task need style or domain behavior beyond prompting? Consider fine-tuning only after eval evidence.
5. Does the task need human approval? Add a workflow, not just a bigger model.

## Task mapping

- Guest response generation: Azure OpenAI.
- Embeddings: Azure OpenAI embeddings model.
- Search and RAG retrieval: Azure AI Search.
- Sentiment and PII: Azure AI Language.
- Translation: Azure AI Translator.
- Voice input/output: Azure AI Speech.
- Invoice/menu document extraction: Document Intelligence.
- Menu photo analysis: Azure AI Vision.
- Safety moderation: Azure AI Content Safety and Azure OpenAI content filters.
