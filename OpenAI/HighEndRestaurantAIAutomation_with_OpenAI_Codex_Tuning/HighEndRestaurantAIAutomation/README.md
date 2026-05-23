# High-End Restaurant AI Automation - Azure AI-102 Practice Project

This repository is a Codex-ready implementation scaffold for a luxury restaurant AI automation platform. It is designed to practice the AI-102 study guide checkpoints while building a realistic multi-service Azure AI solution.

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
