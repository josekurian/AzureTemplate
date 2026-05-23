# Codex Implementation Brief

## Goal
Implement a production-grade sample named **High-End Restaurant AI Automation** using Azure AI services and AI-102 certification practices.

## Architecture summary

```
Guest Web / Bot / Voice
        |
FastAPI Concierge API
        |
Restaurant Orchestrator
        |
+----------------------+-------------------+---------------------+
| Azure OpenAI         | Azure AI Search   | Azure Content Safety |
| Azure Speech         | Azure Translator  | Azure Language       |
| Azure Vision         | Document Intel    | App Insights         |
+----------------------+-------------------+---------------------+
        |
Key Vault + Managed Identity + RBAC + Azure Monitor
```

## Required implementation order

1. Implement configuration and authentication.
2. Implement Azure OpenAI chat and embeddings.
3. Implement AI Search ingestion and query.
4. Implement Content Safety pre-check and post-check.
5. Implement Language PII detection and sentiment.
6. Implement Translator.
7. Implement Speech STT/TTS.
8. Implement Document Intelligence extraction.
9. Implement Vision image analysis.
10. Implement monitoring and test dashboards.
11. Add CI/CD and Bicep deployment.
12. Complete Responsible AI artifacts.

## Critical AI-102 design rules

- Use Azure AI Search for retrieval. Do not ask GPT to invent restaurant policy answers.
- Use Document Intelligence for structured invoices and contracts, not Vision OCR.
- Use Azure AI Language for deterministic PII/sentiment/key phrases, not GPT unless generation or reasoning is required.
- Use Azure Translator for translation, not Azure AI Language.
- Use Azure Speech for STT/TTS, not a text-only model.
- Use Content Safety and Prompt Shields around LLM inputs, retrieved documents, and outputs.
- Prefer Managed Identity + RBAC over stored keys for Azure-hosted workloads.
- Keep endpoint, deployment name, model family, API version, and SDK configuration separate.
- Monitor tokens, latency, HTTP 429, error rate, content-filtered requests, and cost drivers.
- Document rollback, risk mitigations, and human review triggers.

## Deliverables Codex should complete

- Working FastAPI endpoints.
- Azure SDK implementations replacing mock branches.
- IaC deployment using Bicep.
- Search index creation and ingestion.
- Evaluation tests and red-team safety tests.
- CI/CD pipeline.
- Monitoring KQL queries and dashboard notes.
- Complete runbook.
