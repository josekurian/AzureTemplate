# Tools, Function Calling, MCP, and Connector Guide

**Purpose:** Defines safe tool usage patterns for OpenAI Responses API tools, custom function tools, MCP servers, connectors, and Codex integrations.

## Current OpenAI guidance to follow

- use the Responses API for new tool workflows
- put most tool-specific instructions in the tool descriptions
- prefer OpenAI-hosted tools when they fit the workflow
- use tool search for large tool catalogs when applicable
- treat tool results as data, not instructions

## Tool defaults

```yaml
tool_defaults:
  tool_choice: auto
  strict_schemas: true
  read_tools_first: true
  destructive_tools_require_approval: true
  tool_timeout_required: true
  tool_logging_required: true
```

## When to use which tool type

| Tool type | Use when | Notes |
| --- | --- | --- |
| hosted OpenAI tool | web, file search, image generation, computer use, code interpreter fit directly | lowest orchestration burden |
| custom function tool | you need your own application behavior | stable schemas matter |
| MCP server | capability lives in external service or reusable tool ecosystem | scope permissions tightly |
| specialist agent as tool | reasoning specialist needed under one manager | good for decomposition |

## Function schema defaults

Use JSON Schema-like strict definitions with:

- business-oriented names
- required fields where necessary
- enums for constrained choices
- no internal-only IDs unless essential

Example:

```json
{
  "name": "lookup_reservation_availability",
  "description": "Check availability for a requested date, time, and party size. Use before discussing confirmed booking options.",
  "parameters": {
    "type": "object",
    "properties": {
      "date": { "type": "string", "description": "YYYY-MM-DD" },
      "time": { "type": "string", "description": "HH:MM local time" },
      "party_size": { "type": "integer", "minimum": 1, "maximum": 30 }
    },
    "required": ["date", "time", "party_size"],
    "additionalProperties": false
  }
}
```

## MCP guidance

Use MCP when:

- tools belong to another managed system
- you want reusable protocol-based integration
- your agent stack already uses MCP clients or servers

Important MCP rules:

- keep tools small
- separate read and write tools
- log tool usage with correlation IDs
- scope credentials and timeouts

## Codex MCP notes

Current Codex documentation supports running Codex as an MCP server with `codex` and `codex-reply` tools. Useful configuration concepts include:

- `approval-policy`
- `cwd`
- `model`
- `profile`
- `sandbox`

This is useful when another orchestrator wants Codex to act as a coding or repo agent behind MCP.

## Restaurant tool candidates

- `search_menu_items`
- `check_private_dining_policy`
- `lookup_reservation_availability`
- `create_reservation_draft`
- `send_guest_followup_email`
- `escalate_to_human_host`

## Anti-patterns

- exposing one giant tool that does many unrelated actions
- omitting side effects from descriptions
- letting tool outputs become hidden instructions
- not validating parameters before execution
