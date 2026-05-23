# Security and Privacy Tuning Guide

**Purpose:** Protects secrets, identities, guest data, and tool permissions.

## Authentication and authorization

- Prefer managed identity for Azure-hosted compute.
- Assign least-privilege RBAC roles.
- Store unavoidable secrets in Key Vault.
- Rotate keys without downtime using dual-key strategy.
- Use private endpoints for production where appropriate.

## Data protection

- Classify data before sending to any model.
- Redact PII when not required for the task.
- Do not log raw prompts when they may contain sensitive data.
- Use pseudonymous correlation IDs.
- Define retention windows for logs and transcripts.

## Agent permissions

- Read-only tools by default.
- Explicit approval for write actions.
- No direct payment processing in LLM context.
- Human handoff for high-risk guest issues.
