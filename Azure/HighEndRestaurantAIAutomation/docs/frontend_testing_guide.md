High-End Restaurant AI Automation — Frontend Testing Guide

Overview

This document describes all implemented capabilities (backend + frontend) and step-by-step instructions to test them via the frontend harness included in frontend/.

Quick status
- Backend: FastAPI app with episode orchestration, agent runtime, adapters (mock-capable), ingestion/extraction/review stubs, telemetry middleware.
- Frontend: Vite+React app with Dashboard, Episodes, Agents views. Episodes view can execute backend episode workflows.
- Dockers: backend and frontend Dockerfiles plus docker-compose.yml for local integration (build required).
- Tests: pytest unit tests for adapters, agent runtime, ingestion/extraction, and health; run in mock mode.

Implemented capabilities (ready for frontend testing)

1) Platform health & readiness
- Endpoints: GET /health, GET /ready
- Frontend: Dashboard -> Overview shows service name and mock_mode
- Test: open Overview and Run "episode-1" via Episodes to verify.

2) Episode runner (core test harness)
- Endpoint: POST /api/dashboard/run/{episode_id}
- Implemented episodes:
  - episode-1: health and readiness
  - episode-2: document extraction (uses DocumentIntelligenceAdapter in mock_mode)
  - episode-3: knowledge ingestion (embed + index via orchestrator in mock_mode)
  - episode-4: intent detection (nlp.detect_intent)
  - episode-5: human review queue (enqueue/list)
  - episode-6: speech + agent runtime (transcribe, synthesize, sample agent tool invocation)
- Frontend: Episodes view lists episodes and includes "Run" button to execute and show result via alert (expandable later).

3) Dashboard APIs
- GET /api/dashboard/summary — service summary (used by Overview)
- GET /api/dashboard/catalog — episodes/agents/workflows
- GET /api/dashboard/episodes — list episodes (Episodes view)
- GET /api/dashboard/agents — list agents (Agents view)
- GET /api/dashboard/workflows — list workflows
- GET /api/dashboard/metrics — metrics snapshot (http metrics, scenario runs)
- GET /api/dashboard/requests — recent http and scenario requests

4) Agent runtime & tools
- AgentRuntime under app/agent_runtime supports registering tools and invoking them from agents.
- SampleAgent demonstrates a search tool invocation; exercised by episode-6.

5) Ingestion & extraction stubs
- IngestionOrchestrator: embedding + index flow (mock). Triggered by episode-3.
- Document extractor: DocumentIntelligenceAdapter used by episode-2 (mock mode default).
- Human review queue: queue/list operations used by episode-5.

6) Adapters
- AzureOpenAIAdapter: chat, embed (mock fallback). In non-mock mode it calls the Azure OpenAI REST endpoint if OPENAI_ENDPOINT + deployment names are set.
- CognitiveSearchAdapter: index_documents and search (uses azure-search-documents when available; mock fallback).
- DocumentIntelligenceAdapter: calls DocumentAnalysisClient when configured; mock fallback.

How to run locally (backend)
1. cd Azure/HighEndRestaurantAIAutomation
2. python -m venv .venv && source .venv/bin/activate
3. pip install -r requirements.txt
4. cp .env_Azure .env and edit as needed (MOCK_MODE=true by default)
5. make run (starts uvicorn on port 8000)

How to run frontend locally (dev)
1. cd frontend
2. npm install
3. npm run dev (Vite dev server). When running frontend dev, set proxy or call backend at http://localhost:8000 (both run on same machine).

How to build and run containers with docker-compose
1. From repo root: docker-compose build
2. docker-compose up --detach
3. Backend: http://localhost:8000, Frontend: http://localhost:8081
Note: Docker daemon required. If build fails, check Dockerfile contexts in frontend/ and root Dockerfile.

How to test via frontend (step-by-step)
1. Start backend (make run) and frontend dev (npm run dev) or start via docker-compose.
2. Open frontend URL (http://localhost:8081 if docker; Vite will show port when running).
3. Overview: confirm service name and mock_mode.
4. Episodes: click Run on episode-2 (Document Extraction) — in mock mode this returns mocked invoice fields.
5. Episodes: run episode-3 (Ingestion) — returns ingested count.
6. Episodes: run episode-6 (Speech & Agent) — returns mocked transcript, synthesized audio path, and agent_result.
7. Agents: open Agents view to confirm list of agents and types.
8. Dashboard -> Metrics: view recent requests and scenario runs.

Running tests
- Run full test suite: pytest -q (from Azure/HighEndRestaurantAIAutomation). Tests are designed to run in mock mode.
- Run a single test file: pytest tests/test_health.py -q
- Run adapter tests: pytest tests/test_adapters.py -q

Environment variables and .env_Azure
- A .env_Azure file is included listing all required env vars and short explanations. By default MOCK_MODE=true.
- To run against live Azure resources, set MOCK_MODE=false and fill credentials and endpoints.

Limitations and important notes
- Default is MOCK_MODE=true. Live service calls require setting MOCK_MODE=false and valid Azure credentials (service principal or az login for DefaultAzureCredential).
- Some adapter functionality uses azure-* SDKs; ensure corresponding packages are installed for production runs.
- Frontend currently provides Overview, Episodes runner, and Agents list. Additional views (Search, Ingest upload form, Document viewer, Review UI) are placeholders to be implemented.
- Docker builds in this environment previously failed due to missing Docker daemon or context issues — verify Docker locally.

Next steps for full E2E coverage (recommended)
1. Implement frontend forms for document upload and live ingestion; wire to a POST /api/ingest endpoint (create file upload API in backend).
2. Add playback UI for synthesized audio and file download for extraction outputs.
3. Add integration tests (Playwright) that exercise frontend flows with a test backend in mock mode and with an optional Azure-backed integration environment.
4. Replace mock implementations with live adapter code by setting MOCK_MODE=false and following the PR checklist.

Where code lives (key paths)
- Backend entry: app/main.py
- Routers and business logic: app/ (agents, services, ingestion, extraction, review, nlp, speech)
- Frontend: frontend/src/
- Tests: tests/
- Infra scaffold: infra/bicep/
- Env template: .env_Azure

Contact / support
- If you want, provide Azure credentials (via secure channel) and I can finish wiring one adapter end-to-end and add live integration tests.


Document created at: docs/frontend_testing_guide.md

Ready to update this doc with screenshots or Playwright test scripts on request.