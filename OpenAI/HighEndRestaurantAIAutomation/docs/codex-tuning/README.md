# Codex and OpenAI Tuning Index

**Purpose:** Central index for practical tuning guidance used by Codex sessions, OpenAI API applications, Azure OpenAI applications, and hybrid agent workflows in this repository.

## How to use this folder

Use these files as operating guides, not just reference notes. Each guide now includes:

- recommended defaults
- example values
- explanations of why the defaults work
- tuning options to change when requirements shift
- future-proofing notes for adding new capabilities later

## Recommended reading order

1. `agents.md`
2. `prompts.md`
3. `context_engineering.md`
4. `tool_use_and_mcp.md`
5. `model_selection.md`
6. `evals_and_quality.md`
7. the specific optimization guide for your current concern

## Global default stack

Use these defaults unless a stronger requirement overrides them:

| Area | Default | Why |
| --- | --- | --- |
| API surface | Responses API | recommended by OpenAI for new projects |
| primary reasoning model | `gpt-5.5` | strong general default for reasoning and tools |
| fast model | `gpt-5.4-mini` or equivalent fast deployment | lower-cost routing and transformations |
| embeddings | `text-embedding-3-large` | best default retrieval quality |
| multi-turn state | `previous_response_id` | better state handling than raw message replay |
| structured data | JSON Schema structured outputs | more reliable machine-readable responses |
| prompt shape | stable prefix first | improves caching and consistency |
| tool guidance | tool description first | keeps prompts smaller and cleaner |

## Maintenance rules

- update these docs when prompts, models, tools, or retrieval patterns change
- keep sample values realistic and copyable
- state changed defaults explicitly
- add anti-patterns when a team mistake starts repeating
