Title: Azure: Implementations + Live-integration checklist

Summary:
This branch contains the Azure High-End Restaurant AI Automation episode stubs, adapters (mock-capable), infra Bicep scaffolds, Dockerfiles, tests, and documentation. It shows how to proceed to wire real Azure services. Use this PR to review changes and follow the checklist below to complete live integrations.

Checklist to complete live integrations and production readiness:

1) Credentials & Environment
   - Set up service principal or use `az login` for DefaultAzureCredential.
   - Store secrets in Key Vault and populate KEY_VAULT_NAME.
   - Update .env_Azure (set MOCK_MODE=false) or set env vars in CI:
     AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_SUBSCRIPTION_ID
     OPENAI_ENDPOINT, OPENAI_DEPLOYMENT_CHAT, OPENAI_DEPLOYMENT_EMBED, OPENAI_API_KEY (optional)
     SEARCH_SERVICE_NAME, SEARCH_API_KEY (or use managed identity)
     DOCINT_ENDPOINT (Document Intelligence endpoint)
     STORAGE_CONNECTION_STRING (or use managed identity + blob)
     REDIS_URL (Azure Cache for Redis)

2) SDKs & Dependencies
   - Install production Azure SDKs:
     pip install azure-identity azure-ai-openai azure-search-documents azure-ai-documentanalysis azure-ai-vision azure-cognitiveservices-speech
   - Pin versions and update requirements.txt if necessary.

3) Adapters
   - Replace mock-mode behavior by ensuring env and credentials available.
   - Validate AzureOpenAIAdapter.chat/embed REST shapes or replace with azure-ai-openai client when available.
   - Validate CognitiveSearchAdapter indexing (upload_documents) and search iteration shapes.
   - Validate DocumentIntelligenceAdapter extraction field mapping for your document models.

4) Infra & Indexing
   - Run `az bicep build --file infra/bicep/main.bicep` to validate templates.
   - Deploy infra to a test resource group; configure private endpoints if required.
   - Build Cognitive Search index schema and load data using scripts/build_search_index.py and scripts/ingest_documents.py (adapt these to your schema).

5) Caching & Performance
   - Provision Azure Cache for Redis; set REDIS_URL and validate Cache.connect().
   - Implement embedding caching via Cache service to avoid duplicate embedding calls.
   - Add adaptive model selection in adapters to reduce cost for low-value queries.

6) CI/CD
   - Update GitHub Actions secrets: AZURE_CREDENTIALS (service principal JSON), KEY_VAULT_NAME, OPENAI_API_KEY, SEARCH_API_KEY.
   - Add infra validation step (`az bicep build`) and optional `az deployment group create` for staging if appropriate.

7) Docker & Local Integration Tests
   - Ensure Docker daemon is available and `docker-compose build` from repo root.
   - Update Dockerfile contexts if needed; run `docker-compose up --build` and run `make smoke`.

8) Observability & Ops
   - Configure Application Insights: set APPINSIGHTS_CONNECTION_STRING and instrument adapters and runtime.
   - Create KQL dashboards for latency, tokens, errors, safety blocks, and throttling.

9) Responsible AI
   - Configure pre/post Content Safety thresholds and blocklists.
   - Add evals to verify outputs against red-team prompts and include results in docs/evals.

10) Security Review
   - Ensure no secrets committed; run secret scanning and policy-as-code checks.
   - Validate RBAC and least-privilege identities for each service.

Dev notes:
- This branch keeps MOCK_MODE default true. Set MOCK_MODE=false for real runs.
- Tests in `tests/` are designed to run in mock mode and to validate integration flows. Add integration tests that require Azure resources guarded behind a pytest marker (e.g., @pytest.mark.integration).

Request:
- Please review, then open a PR on GitHub from branch `azure/live-integration-checklist` into `main` and mark it as draft if you prefer incremental work.

