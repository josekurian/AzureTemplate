# Evaluation and Quality Guide

**Purpose:** Defines regression evaluation, prompt tests, and quality gates.

## Evaluation layers

- Unit tests for deterministic logic.
- Prompt regression tests for known scenarios.
- RAG answer tests for citation correctness and groundedness.
- Red-team tests for jailbreak, prompt injection, unsafe allergy claims, and PII leakage.
- Latency and cost tests for budget adherence.

## Quality rubric

Score every generated answer on:

- Correctness.
- Groundedness.
- Completeness.
- Tone and brand alignment.
- Safety.
- Privacy.
- Citation/source quality.
- Escalation behavior.

## Gate before release

- No critical safety failures.
- No fabricated reservation confirmations.
- No unsupported allergy guarantees.
- No source-free policy answers.
- P95 latency within target.
- Cost per conversation within budget.
