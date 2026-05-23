# Observability and Monitoring Guide

**Purpose:** Defines logs, metrics, traces, dashboards, and alerts for OpenAI, Azure AI, and Codex-assisted workflows.

## Core telemetry defaults

```yaml
telemetry_defaults:
  request_id: required
  pseudonymous_user_id: required
  model_and_deployment: required
  latency_by_stage: required
  token_usage: required_when_available
  retrieval_trace: required_for_rag
  safety_events: required
  tool_events: required
```

## Minimum event fields

- request ID
- session or conversation ID
- route or feature name
- model name
- deployment name if applicable
- reasoning effort
- verbosity
- input tokens
- cached tokens
- output tokens
- tool count
- latency per step
- success or failure

## RAG telemetry

Log:

- query text or safe hash
- top document IDs
- chunk count sent to model
- filter criteria
- stale-document flags

## Safety telemetry

Log:

- category and severity
- block or allow decision
- escalation path
- redaction applied
- prompt injection suspicion flag

## Codex-specific telemetry

If Codex is used operationally, log:

- active model and reasoning settings
- tool usage by type
- approvals triggered
- subagent counts
- compaction frequency
- MCP server failures

Current Codex config supports OpenTelemetry export. Example starter config:

```toml
[otel]
environment = "dev"
trace_exporter = "otlp-http"
metrics_exporter = "otlp-http"
log_user_prompt = false
```

Keep `log_user_prompt = false` by default unless you have strong privacy approval and need.

## Dashboards to maintain

### Guest experience

- p50 and p95 latency
- answer failure rate
- escalation rate
- user rating or thumbs feedback

### Cost and efficiency

- input tokens
- cached tokens
- output tokens
- cost by route
- retrieval cost
- speech and document usage

### Safety

- block rate
- prompt injection detections
- PII redactions
- human escalation counts

### Reliability

- 429s
- 5xx responses
- retry counts
- tool failure rate
- MCP initialization failures

## Alert examples

- p95 latency exceeds target for 15 minutes
- cached-token rate drops by 40 percent
- tool failure rate exceeds threshold
- safety block rate spikes after a prompt change
- retrieval returns zero results above normal baseline

## Anti-patterns

- only logging final text and not the path that produced it
- skipping token logging, then trying to debug cost later
- logging raw sensitive prompts without approval and retention policy
