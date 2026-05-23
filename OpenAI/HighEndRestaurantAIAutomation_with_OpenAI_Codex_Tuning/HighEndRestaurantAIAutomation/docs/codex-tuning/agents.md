# Agent Design Guide

**Purpose:** Defines agent roles, boundaries, handoffs, memory rules, and tool usage patterns.

## Applies to this project

Use these instructions for the High-End Restaurant AI Automation sample app. The app demonstrates AI-102 practices using Azure OpenAI, Azure AI Search, Azure AI Content Safety, Azure AI Language, Azure AI Translator, Azure AI Speech, Azure AI Document Intelligence, Azure AI Vision, Azure AI Face, Custom Vision placeholders, Bot integration, monitoring, CI/CD, responsible AI, and cost controls.

## Non-negotiable engineering rules

- Prefer small, testable changes over large rewrites.
- Preserve the existing FastAPI structure unless the change explicitly requires restructuring.
- Use secure configuration: environment variables, managed identity, Key Vault references, and RBAC. Never hardcode secrets.
- Add or update tests for every behavior change.
- Run linting, type checks, unit tests, and smoke tests before declaring a task complete.
- Document service selection decisions, especially when a simpler Azure AI service is better than a generative model.
- Maintain a responsible AI risk note for every user-facing AI capability.


## Agent roles

### Concierge Agent

Handles guest-facing chat, reservation questions, menu recommendations, event inquiries, and private dining FAQs. It must ground answers in Azure AI Search results and never invent availability, prices, or policies.

### Menu Intelligence Agent

Analyzes menu data, image uploads, seasonal specials, wine pairing notes, dietary tags, and allergen metadata. It uses Vision for images, Document Intelligence for structured menus or supplier forms, and Azure OpenAI only for prose explanations.

### Reservation Operations Agent

Prepares reservation summaries, detects special occasions, routes VIP requests, and generates staff notes. It must not finalize reservations unless connected to a real booking system tool with confirmed availability.

### Safety and Compliance Agent

Screens prompts, outputs, and retrieved context. It enforces content filters, blocklists, PII redaction, allergy disclaimer policy, and human escalation rules.

### Knowledge Curator Agent

Maintains the retrieval corpus. It validates chunk quality, metadata, versioning, duplicate detection, stale document retirement, and index rebuild procedures.

### Evaluation Agent

Runs regression cases, red-team prompts, latency tests, cost checks, and answer-quality rubrics. It compares current behavior to baseline.

## Handoff rules

- Concierge to Safety: before any generated response is returned.
- Concierge to Reservation Operations: when a guest requests booking, modification, cancellation, private dining, or payment.
- Menu Intelligence to Safety: when allergy, health, dietary, or protected-class content appears.
- Knowledge Curator to Evaluation: after every index schema or chunking change.

## Agent memory rules

- Store stable business facts in AI Search, not in conversation memory.
- Store session-specific preferences only for the active session unless the user explicitly opts in.
- Never store payment details, government IDs, health details, or sensitive PII in agent memory.
- Summarize long conversations into task state: guest intent, constraints, confirmed facts, pending questions, and next action.
