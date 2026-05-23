# Skills and Capability Map

**Purpose:** Defines reusable implementation skills Codex should apply when building the sample app.

## Applies to this project

Use these instructions for the High-End Restaurant AI Automation sample app. The app demonstrates AI-102 practices using Azure OpenAI, Azure AI Search, Azure AI Content Safety, Azure AI Language, Azure AI Translator, Azure AI Speech, Azure AI Document Intelligence, Azure AI Vision, Azure AI Face, Custom Vision placeholders, Bot integration, monitoring, CI/CD, responsible AI, and cost controls.

## Non-negotiable engineering rules

- Prefer small, testable changes over large rewrites.
- Preserve the existing FastAPI structure unless the change explicitly requires restructuring.
- Use secure configuration: environment variables, managed identity, Key Vault references, and RBAC. Never hardcode secrets.
- Add or update tests for every behavior change.
- Run linting, type checks, unit tests, and smoke tests before declaring a task complete.
- Document service selection decisions, especially when a simpler Azure AI service is better than a generative model.
- Maintain a responsible AI risk note for every user-facing AI capability.


## Skill: Azure AI service selection

Use the least complex correct service. Use Azure AI Language for sentiment, PII, key phrases, named entity recognition, CLU, and deterministic NLP. Use Translator for language conversion. Use Speech for STT/TTS. Use Document Intelligence for structured form extraction. Use Vision for image analysis and OCR from photos. Use Azure AI Search for retrieval, semantic search, vector search, and RAG grounding. Use Azure OpenAI for generation, reasoning, summarization, embeddings, and multi-turn natural-language interactions.

## Skill: Retrieval augmented generation

- Chunk restaurant policies, menus, allergy rules, event packages, and reservation rules.
- Store chunks in Azure AI Search with metadata: document type, audience, effective date, cuisine, allergen, and confidentiality.
- Use embeddings for vector recall and semantic ranking for precision.
- Keep citations and source IDs in the final answer.
- Refuse or ask a follow-up when retrieved evidence is insufficient.

## Skill: Safety-first response generation

- Run user prompts and retrieved documents through Azure AI Content Safety when the task uses LLM context.
- Enable Prompt Shields style checks for direct user prompt attacks and indirect document attacks.
- Block or escalate high severity content.
- Use blocklists for prohibited business terms, disallowed discounts, unsafe medical/allergy advice, and regulated claims.

## Skill: Multi-modal restaurant automation

- Menu image ingestion: Azure AI Vision.
- Supplier invoice extraction: Document Intelligence.
- Guest sentiment and PII detection: Azure AI Language.
- Multilingual chat: Translator and Azure OpenAI.
- Voice concierge: Speech STT and TTS.
- Knowledge search: AI Search.
- Personalized response generation: Azure OpenAI.

## Skill: Production readiness

- Managed identity and RBAC by default.
- Key Vault only when API keys are unavoidable.
- Azure Monitor metrics, Application Insights, Diagnostic Settings, and Log Analytics KQL.
- Budgets and alerts for token spend, search units, document pages, and speech hours.
- Blue/green or canary deployment for application and model changes.
