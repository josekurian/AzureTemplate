# Codex Workflow Playbook

**Purpose:** Provides repeatable workflows for using Codex effectively in this repository and similar OpenAI-connected engineering environments.

## Default workflow profile

```yaml
workflow_defaults:
  read_project_instructions_first: true
  smallest_safe_change: true
  targeted_tests_first: true
  doc_updates_in_same_change: true
  summarize_risks_on_completion: true
```

## Feature workflow

1. Read the relevant instructions.
2. Classify the task as code, prompt, retrieval, tool, or infra work.
3. Build the smallest working path first.
4. Add or update tests.
5. Validate locally with targeted checks.
6. Update docs if behavior or defaults changed.

## Bugfix workflow

1. Reproduce or model the issue.
2. Add regression coverage when feasible.
3. Fix root cause.
4. Re-run the narrow failing path.
5. Check for cost, safety, or latency side effects.

## Refactor workflow

1. Preserve behavior with tests.
2. Move in small steps.
3. Re-run validation after each logical stage.
4. Keep prompts and tool contracts stable unless intentionally versioned.

## Codex tuning notes

Suggested starting config:

```toml
model = "gpt-5.5"
model_reasoning_effort = "medium"
model_verbosity = "medium"
approval_policy = "on-request"
sandbox_mode = "workspace-write"
web_search = "cached"
```

## Anti-patterns

- large rewrites before a narrow path works
- changing prompts without eval updates
- broad validation before targeted validation
