# Coding Standards for Codex

**Purpose:** Defines implementation standards for human developers and coding agents, with defaults that support maintainability, testability, and safe AI integration.

## Core defaults

```yaml
python_defaults:
  type_hints: required_on_public_functions
  pydantic_at_boundaries: true
  service_timeout_required: true
  dependency_injection: preferred
  global_mutable_state: avoid
  structured_logging: preferred
```

## Python standards

- Use type hints for public functions, API models, and service interfaces.
- Prefer Pydantic models at API and tool boundaries.
- Keep external AI and Azure clients behind adapter layers that are easy to mock.
- Separate orchestration from pure business logic.
- Keep retries and timeouts in the integration layer, not scattered across business code.

## AI integration standards

- Prefer structured outputs instead of parsing free text.
- Prefer deterministic helpers for validation, parsing, sorting, filtering, and formatting.
- Keep model prompts versioned and reviewable.
- Log model name, deployment name, latency, token usage, and tool calls where available.

## Error handling defaults

| Area | Default | Reason |
| --- | --- | --- |
| outbound calls | explicit timeout | prevents hangs |
| transient failures | bounded retry with backoff | improves reliability |
| user responses | safe, minimal messages | protects internals |
| logs | full technical detail | supports debugging |
| safety failure | fail closed for risky flows | safer than silent pass-through |

## Sample timeout defaults

```yaml
timeouts_seconds:
  openai_text_generation: 30
  search_query: 5
  content_safety: 3
  embeddings: 10
  document_intelligence_start: 10
  document_intelligence_poll: async
```

Adjust by endpoint, but keep explicit values rather than library defaults.

## Tool and schema standards

- Use business-oriented parameter names.
- Use enums for fields such as meal period, dining area, reservation state, and language code.
- Validate user input before passing it to a model or external tool.
- Return structured errors that the orchestrator can safely interpret.

## Testing standards

- Add or update tests for every behavior change.
- Prefer targeted unit or boundary tests first.
- Use fixtures for representative retrieval results and tool responses.
- Do not rely on live model wording in CI unless you have a stable eval harness.

## Documentation standards

- If a change alters prompt shape, context size, model choice, or tool behavior, update the tuning docs.
- Record defaults and example values close to the code or config that uses them.
- Explain non-obvious guardrails in comments or nearby docs.

## Pull request checklist

- tests added or updated
- docs updated
- no secrets introduced
- cost impact considered
- safety impact considered
- rollout and rollback understood
