# Test Generation Guide

**Purpose:** Explains how Codex should create useful tests and avoid superficial coverage.

## Test types

- Service boundary tests: verify correct Azure AI service selection.
- Prompt construction tests: verify stable prefix and compact variable context.
- Safety tests: verify unsafe inputs are blocked or escalated.
- RAG tests: verify sources are cited and unsupported claims are refused.
- API contract tests: verify request/response schemas.
- Integration smoke tests: verify deployed service health.

## Good test pattern

- Arrange clear inputs.
- Mock external services.
- Assert business behavior and safety behavior.
- Check telemetry where appropriate.

## Avoid

- Tests that only assert objects are not null.
- Tests that depend on live AI output without a stable evaluation strategy.
- Tests that require real secrets in CI.
