# Cost Optimization Guide

**Purpose:** Controls token, search, speech, document processing, logging, and deployment costs.

## Cost principles

- Use deterministic Azure AI services before OpenAI when the task is classification, translation, OCR, or structured extraction.
- Use smaller models for routing and summarization when quality is sufficient.
- Cap output tokens and avoid verbose responses by default.
- Use batch or asynchronous processing for offline tasks.
- Monitor token usage, search units, document pages, speech hours, image transactions, and log volume.

## Restaurant examples

- Use Translator for translating menu descriptions; do not use a large language model for routine translation.
- Use Document Intelligence for supplier invoices; do not ask a chat model to parse invoices from raw OCR text unless business rules require reasoning.
- Use AI Search for policies; do not paste all policies into every prompt.
- Use Content Safety classifiers before expensive generation when an input should be blocked early.

## Budget alerts

Create alerts for:

- Daily token spend.
- 429 throttling events.
- Search unit utilization.
- Document page volume spikes.
- Speech transcription hours.
- Log Analytics ingestion volume.
