# AI-102 Practice Checkpoints Mapped to This Project

## Checkpoint 1: Explain why each service was chosen
Use `docs/service_selection_matrix.md` and include a rationale in every PR.

## Checkpoint 2: Call each service from code using secure configuration
Adapters under `app/services/` must use `DefaultAzureCredential`, deployment names, endpoints, and API versions from config.

## Checkpoint 3: Rotate credentials without downtime / use managed identity
Prefer keyless auth. Use `scripts/rotate_keys.sh` only for services that still require keys.

## Checkpoint 4: Show dashboards for latency, errors, token usage, and content safety
Use `docs/monitoring_kql.md`. Track total tokens, 429 throttling, error rate, P95 latency, and safety blocks.

## Checkpoint 5: Redeploy from source control using CI/CD
Use `infra/bicep/main.bicep`, `pipelines/azure-pipelines.yml`, and `.github/workflows/deploy.yml`.

## Checkpoint 6: Document Responsible AI risks, mitigations, test results, rollback
Use `docs/responsible_ai_risk_register.md` and `evals/red_team_prompts.json`.
