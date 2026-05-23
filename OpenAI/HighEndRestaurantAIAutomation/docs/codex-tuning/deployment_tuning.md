# Deployment, CI/CD, and Rollback Tuning Guide

**Purpose:** Defines safe deployment practices for code, prompts, model configs, indexes, and agent settings.

## Deployable artifact classes

- application code
- infrastructure as code
- prompt templates
- tool schemas
- model selection config
- evaluation datasets
- search index schema
- safety thresholds and blocklists
- Codex config and instruction files

## Recommended default pipeline

```yaml
pipeline_defaults:
  static_checks: required
  unit_tests: required
  prompt_regressions: required
  safety_regressions: required
  targeted_smoke_test: required
  manual_prod_approval: true_for_risky_ai_changes
```

## Versioning rules

Version separately when possible:

- prompts
- retrieval schema
- model/deployment mapping
- safety policy

This makes rollback cleaner than bundling everything into one opaque change.

## Release stages

### Development

- cheap and fast defaults are acceptable
- broader logging is fine
- use synthetic or sanitized data

### Staging

- production-like prompts and tool permissions
- eval gates enforced
- realistic latency and cost measurement

### Production

- pinned defaults for prompts and deployments
- strict observability
- rollback-tested releases only

## Rollback defaults

| Artifact | Recommended rollback strategy |
| --- | --- |
| app code | deployment slots, canary, or blue/green |
| prompts | versioned files and version tags |
| model deployment | keep previous deployment available |
| search index | index alias or dual index strategy |
| safety threshold | revert threshold file or policy object |

## OpenAI and Codex-specific notes

- Prefer the Responses API for new work.
- Track model changes explicitly when migrating between GPT generations.
- If Codex instructions change behavior materially, treat those files as deployable artifacts with review and rollback.
- If using Codex or MCP servers operationally, version their config and allowed tool sets.

## Default promotion criteria

Promote only when all are true:

- no critical safety regressions
- no broken structured outputs
- no unsupported reservation or policy claims
- latency within target
- cost within budget or explicitly accepted
- rollback path verified

## Anti-patterns

- Changing prompt, retrieval, model, and safety threshold together without isolated evals
- Releasing a new index without alias fallback
- Promoting to production because qualitative spot checks looked fine
