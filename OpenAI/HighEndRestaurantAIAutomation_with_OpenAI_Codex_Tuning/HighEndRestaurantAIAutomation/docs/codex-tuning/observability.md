# Observability and Monitoring Guide

**Purpose:** Defines logs, metrics, traces, dashboards, and alerts.

## Required telemetry

- Request ID and user/session pseudonymous ID.
- Route and feature name.
- Azure service called.
- Latency by service.
- Input tokens, output tokens, cached tokens when available.
- Search query, document IDs retrieved, and result count.
- Safety category scores and block decisions.
- Tool call success/failure.
- Error codes and retry counts.

## Dashboards

- Guest experience: latency, errors, escalation rate, answer ratings.
- Cost: tokens, cached tokens, search units, speech hours, document pages.
- Safety: blocked prompts, prompt injection attempts, blocklist matches.
- Reliability: 429 rate, 5xx errors, circuit breaker open events.

## KQL examples to maintain

Keep KQL queries in `docs/monitoring_kql.md` for throttling, safety blocks, error rates, and latency percentiles.
