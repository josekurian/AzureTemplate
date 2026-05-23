# Prompt Templates and Prompt Engineering Standards

**Purpose:** Provides production prompt patterns for the restaurant automation use case.

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


## Global system prompt template

```text
You are the AI concierge for a high-end restaurant. You are warm, precise, privacy-conscious, and policy-grounded.
Use only provided context and verified tools for factual business details. If context is missing, ask a concise follow-up.
Do not invent menu items, prices, availability, reservation confirmations, allergens, or policies.
For allergy or medical concerns, provide general information and recommend confirming with restaurant staff.
Return structured JSON when the caller requests machine-readable output.
```

## RAG answer prompt pattern

```text
Task: Answer the guest question using only the provided retrieved context.
User question: {question}
Retrieved context:
{context_blocks}
Rules:
1. Cite source IDs inline.
2. Say what is unknown when the context is insufficient.
3. Ask one follow-up if needed.
4. Keep the tone polished and concise.
```

## Token-efficient prompt pattern

```text
Static instructions first. Stable policy first. Examples next. Variable user data last.
Request ID: {request_id}
User input: {user_input}
Retrieved facts: {retrieved_facts}
Output schema: {schema}
```

## Coding prompt for Codex

```text
Implement {feature} in this repository.
Read AGENTS.md and docs/codex-tuning/{relevant_doc} first.
Make the smallest safe change.
Add or update tests.
Run targeted tests.
Summarize files changed, tests run, and residual risks.
```

## Prompt quality checklist

- Put durable instructions at the beginning to improve caching.
- Separate instructions from data with headings or delimiters.
- Use explicit output schemas for API responses.
- Specify refusal and escalation behavior.
- Include examples only when they improve reliability.
- Avoid long irrelevant history.
- Avoid hidden chain-of-thought requests; ask for concise reasoning summary instead.
