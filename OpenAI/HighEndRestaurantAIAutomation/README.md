# High-End Restaurant AI Automation - Azure AI-102 Practice Project

This repository is a Codex-ready implementation scaffold for a luxury restaurant AI automation platform. It is designed to practice the AI-102 study guide checkpoints while building a realistic multi-service Azure AI solution.

## Episode 3 agentic expansion

This repository now includes an Episode 3-style agentic runtime with:

- specialist agents under `app/agents/`
- typed tool registry and permissions under `app/agent_runtime/` and `app/tools/`
- approval-gated workflows and trace endpoints
- in-memory session memory and approval queue for local practice
- Foundry-oriented agent packaging artifacts in `infra/foundry-agents/`

Key Episode 3 endpoints:

- `POST /agents/chat`
- `GET /agents/trace/{trace_id}`
- `POST /workflows/private-dining`
- `GET /approvals`
- `POST /approvals/{approval_id}`

## Episode 4 NLP expansion

The repository now also includes an Episode 4-style deterministic NLP layer with:

- text analytics and PII redaction under `app/api/nlp.py`
- CLU-style intent/entity routing in `app/services/clu_client.py`
- curated FAQ answering in `app/services/question_answering_client.py`
- translation endpoints in `app/api/translation.py`
- speech, SSML, speech translation, and pronunciation endpoints in `app/api/speech.py`
- multilingual concierge orchestration in `app/orchestrators/nlp_router.py`

Key Episode 4 endpoints:

- `POST /nlp/analyze`
- `POST /nlp/pii/redact`
- `POST /nlp/detect-language`
- `POST /nlp/intent`
- `POST /nlp/qa`
- `POST /nlp/multilingual-chat`
- `POST /translate/text`
- `POST /translate/document`
- `POST /speech/transcribe`
- `POST /speech/synthesize`
- `POST /speech/synthesize-ssml`
- `POST /speech/translate`
- `POST /speech/pronunciation`
- `POST /speech/identify-language`
- `POST /concierge/multilingual-chat`

## Episode 5 knowledge mining expansion

The repository now also includes an Episode 5-style knowledge mining layer with:

- hybrid, vector, keyword, and semantic-style retrieval in `app/services/search_client.py`
- richer index and ingestion scripts in `scripts/build_search_index.py` and `scripts/ingest_documents.py`
- receipt, layout, invoice, and contract extraction in `app/services/document_intelligence_client.py`
- analyzer-driven multimodal extraction in `app/services/content_understanding_client.py`
- analyzer contract samples under `analyzers/`

Key Episode 5 endpoints:

- `POST /search/query`
- `GET /search/ingest-status`
- `POST /document/receipt`
- `POST /document/layout`
- `POST /document/contract`
- `POST /content-understanding/analyze`

## Episode 6 operational knowledge pipeline

The repository now also includes an Episode 6-style ingestion and review layer with:

- deterministic chunking, normalization, and embeddings under `app/ingestion/`
- low-confidence review gating under `app/review/human_review_queue.py`
- richer Episode 6 schemas in `app/schemas_episode6.py`
- `v2` search and extraction endpoints with facets, grounding, query logs, and review-aware ingestion
- search and analyzer infrastructure contracts under `infra/search/` and `infra/content-understanding/analyzers/`

Key Episode 6 endpoints:

- `POST /search/query/v2`
- `GET /search/query-log`
- `POST /ingestion/jobs`
- `GET /ingestion/jobs`
- `GET /reviews`
- `POST /reviews/{review_id}/approve`
- `POST /reviews/{review_id}/reject`
- `POST /reviews/{review_id}/correct`
- `GET /content-understanding/analyzers`

## Business scenario
A high-end restaurant group wants an AI platform that can:

1. Answer guest questions using a grounded knowledge base.
2. Recommend menus, wine pairings, tasting menus, and private dining packages.
3. Take reservation requests through chat and voice.
4. Translate guest conversations for international visitors.
5. Extract supplier invoice details and event contract data.
6. Analyze plating photos for quality assurance.
7. Moderate guest-generated content and LLM responses.
8. Monitor latency, errors, tokens, throttling, safety blocks, and cost.
9. Use managed identity, Key Vault, RBAC, and no hardcoded secrets.
10. Deploy reproducibly with IaC and CI/CD.

## Azure AI tools covered

| Tool | Restaurant use case | AI-102 practice objective |
|---|---|---|
| Azure OpenAI Service | Concierge chatbot, summarization, menu copy, RAG answers, embeddings | Generative AI, deployment names, endpoints, tokens, content filters |
| Azure AI Search | Restaurant knowledge base, menu and policy retrieval, vector search | Knowledge mining, RAG retrieval layer, index schema |
| Azure AI Vision | Plate image analysis, OCR from menu photos | Computer vision service selection |
| Azure AI Document Intelligence | Supplier invoices, private event contracts, W-9 forms | Information extraction from structured documents |
| Azure AI Language | Sentiment, PII detection, key phrases, CLU-style intent routing | NLP service selection and deterministic NLP |
| Azure AI Translator | Multilingual guest chat and menu translation | Translation boundary vs Language/OpenAI |
| Azure AI Speech | Voice reservation agent, speech-to-text, text-to-speech | Speech solutions, STT/TTS |
| Azure AI Content Safety | Prompt shields, harm detection, blocklists | Responsible AI safeguards |
| Azure AI Face | Optional VIP host check-in / consent-based recognition demo | Face service boundary and responsible use |
| Azure Custom Vision | Optional custom plate-classifier training flow | Custom image classifier practice |
| Azure Bot Service | Omnichannel concierge bot handoff design | Bot lifecycle and channel integration |
| Azure Monitor / App Insights / Log Analytics | Metrics, alerts, KQL dashboards | Monitoring and operational readiness |
| Key Vault / Managed Identity / RBAC | Secure configuration and keyless auth | Security and authentication objectives |

## Recommended Codex workflow

1. Read `CODEX_IMPLEMENTATION_BRIEF.md` first.
2. Implement one service adapter at a time under `app/services/`.
3. Keep `MOCK_MODE=true` until Azure resources are deployed.
4. Use `docs/ai102_practice_checkpoints.md` to verify each Microsoft Learn AI-102 checkpoint.
5. Deploy IaC in `infra/bicep/`.
6. Run tests and smoke tests.
7. Complete the risk register and monitoring dashboard.

## Local quick start

```bash
cd /Users/josekurian/AzureTemplate/OpenAI/HighEndRestaurantAIAutomation
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Open: `http://127.0.0.1:8000/docs`

## Copy this project to the requested Mac path

```bash
mkdir -p /Users/josekurian/AzureTemplate/OpenAI
cp -R HighEndRestaurantAIAutomation /Users/josekurian/AzureTemplate/OpenAI/
```

Or run:

```bash
bash scripts/bootstrap_local.sh
```
