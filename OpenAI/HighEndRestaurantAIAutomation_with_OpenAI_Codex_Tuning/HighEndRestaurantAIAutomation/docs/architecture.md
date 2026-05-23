# Architecture

## Core pattern

The restaurant solution uses a retrieval-augmented generation pattern:

1. Guest input is screened by Azure AI Content Safety.
2. Azure AI Language detects PII, sentiment, and key phrases.
3. Azure AI Search retrieves grounded restaurant facts.
4. Azure OpenAI generates a polished concierge response using only retrieved context.
5. Content Safety screens the output before returning it.
6. App Insights and Azure Monitor record telemetry.

## Why these services

- **Azure OpenAI**: generation, reasoning, summarization, embeddings.
- **AI Search**: retrieval and knowledge mining. This prevents hallucination about menu, pricing, policies, and availability.
- **Language**: deterministic NLP tasks such as sentiment and PII redaction.
- **Translator**: language translation; do not substitute Language or GPT for deterministic translation requirements.
- **Speech**: voice reservations and accessibility.
- **Document Intelligence**: structured fields from invoices and contracts.
- **Vision**: plate images, menu photos, scene/image analysis.
- **Content Safety**: harm detection, prompt shields, blocklists.
