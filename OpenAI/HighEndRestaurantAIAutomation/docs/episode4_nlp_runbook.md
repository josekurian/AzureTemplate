# Episode 4 NLP Runbook

## Operational checks

1. Validate `/nlp/analyze`, `/nlp/intent`, and `/nlp/qa`.
2. Validate `/translate/text` and `/translate/document`.
3. Validate `/speech/transcribe`, `/speech/synthesize-ssml`, `/speech/translate`, and `/speech/pronunciation`.
4. Confirm PII is redacted before any telemetry or downstream generative path.
5. Confirm low-confidence intent routes return clarification or escalation.

## Privacy rules

- Log redacted text only.
- Do not persist raw PII unless required by an approved reservation workflow.
- Treat speech transcripts as sensitive guest data.

## Fallback rules

- translation failure: keep original language and offer human help
- low CLU confidence: ask clarifying question
- low STT confidence: ask guest to repeat or switch to text
- low QA confidence: escalate to grounded retrieval or human review
