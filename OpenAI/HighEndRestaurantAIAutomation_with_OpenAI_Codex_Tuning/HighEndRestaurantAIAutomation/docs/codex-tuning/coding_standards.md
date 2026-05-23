# Coding Standards for Codex

**Purpose:** Defines repository implementation standards for automated coding agents.

## Python standards

- Use type hints for public functions.
- Prefer Pydantic models at API boundaries.
- Keep service clients isolated behind interfaces that are mockable.
- Use dependency injection for clients and configuration.
- Avoid global mutable state except immutable configuration.
- Use explicit timeouts for all network calls.

## Error handling

- Raise domain-specific exceptions from service adapters.
- Convert internal exceptions to safe HTTP responses.
- Log full technical details server-side but return minimal guest-safe messages.
- Treat safety service failures as fail-closed for high-risk workflows.

## Pull request checklist

- Tests added/updated.
- Docs updated.
- No secrets in diff.
- Token/cost impact considered.
- Safety impact considered.
- Rollback plan documented for risky changes.
