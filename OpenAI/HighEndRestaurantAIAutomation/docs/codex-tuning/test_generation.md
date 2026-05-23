# Test Generation Guide

**Purpose:** Explains how Codex and developers should create useful tests for AI-enabled code and avoid superficial coverage.

## Default testing priorities

1. deterministic business logic
2. schema and contract validation
3. retrieval assembly behavior
4. safety policy behavior
5. integration smoke paths
6. model-facing evals

## Test types

### Service boundary tests

Verify:

- correct service selection
- correct timeout or retry settings
- correct error translation

### Prompt construction tests

Verify:

- stable prefix order
- compact dynamic state
- schema presence
- required source IDs in RAG prompts

### Safety tests

Verify:

- unsafe inputs are blocked or escalated
- allergy claims are softened correctly
- PII handling works as designed

### RAG tests

Verify:

- citation presence
- unsupported claims refused
- stale policy not preferred
- adversarial chunk text does not override policy

### API contract tests

Verify:

- request schema
- response schema
- tool parameter validation

## Example default fixture structure

```yaml
tests/fixtures:
  retrieval_chunks/
  tool_outputs/
  prompt_inputs/
  expected_json/
```

## Good test pattern

- arrange realistic input
- mock external services
- assert business behavior
- assert safety behavior
- assert telemetry where relevant

## Anti-patterns

- asserting only that a value is not null
- snapshotting giant prompts without checking important fields
- relying on live model wording in CI without a stable eval strategy
- using real secrets or live billing paths in tests
