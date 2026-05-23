# Deployment, CI/CD, and Rollback Tuning Guide

**Purpose:** Defines safe deployment practices for application, prompts, indexes, and model configs.

## Deployable artifacts

- Application code.
- Infrastructure as code.
- Prompt templates.
- AI Search index schema.
- Evaluation datasets.
- Content Safety thresholds and blocklists.
- Environment configuration.

## CI/CD gates

- Static checks and dependency audit.
- Unit tests.
- Prompt regression tests.
- Red-team safety tests.
- Bicep/Terraform validation.
- Smoke test against staging.
- Manual approval for production if safety-sensitive changes are included.

## Rollback

- Use deployment slots or blue/green strategy.
- Version prompt templates.
- Keep previous AI Search index behind an alias.
- Keep previous model deployment available until new deployment passes evals.
- Roll back content safety policy changes if false positives block legitimate flows.
