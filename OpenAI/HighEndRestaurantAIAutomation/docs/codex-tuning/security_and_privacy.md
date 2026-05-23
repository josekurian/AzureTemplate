# Security and Privacy Tuning Guide

**Purpose:** Protects secrets, identities, guest data, prompt contents, and tool permissions across OpenAI, Azure, and Codex workflows.

## Security defaults

```yaml
security_defaults:
  managed_identity_preferred: true
  least_privilege_rbac: true
  secrets_in_key_vault: true
  raw_prompt_logging: disabled
  pseudonymous_ids: required
  private_endpoints_for_prod: recommended
```

## Authentication and authorization

- Prefer managed identity for Azure-hosted compute.
- Use least-privilege RBAC roles.
- Keep API keys only where unavoidable.
- Rotate keys with overlap, not cutover cliffs.
- Restrict MCP and tool credentials to the minimum scope required.

## Data protection

- classify data before sending it to a model
- redact unnecessary PII before storage or logging
- use pseudonymous correlation IDs
- define retention windows for chat logs and transcripts
- isolate sensitive environments from broad developer access

## Codex-specific guidance

Use project-scoped configuration for project behavior, but keep provider auth and telemetry routing in user-level Codex config when required by current Codex rules.

Recommended security-sensitive Codex defaults:

```toml
approval_policy = "on-request"
sandbox_mode = "workspace-write"
web_search = "cached"

[otel]
log_user_prompt = false
```

### Why these are good defaults

- `on-request`: reduces silent risky actions
- `workspace-write`: limits unintended machine-wide access
- `cached` search: lowers live web exposure when not needed
- `log_user_prompt = false`: avoids unnecessary prompt retention

## Tool permissions

- default to read-only tools
- separate read and write tools
- require human approval for destructive actions
- never expose payment systems directly to unconstrained generation

## Privacy review checklist

- Does the request truly need personal data?
- Can the data be masked or minimized first?
- Is the data stored anywhere after the turn?
- Who can access the logs?
- Is retention documented?

## Anti-patterns

- hardcoding keys
- logging full prompts with PII by default
- giving the model broad write access because it is convenient
- storing guest-sensitive data in chat memory without consent
