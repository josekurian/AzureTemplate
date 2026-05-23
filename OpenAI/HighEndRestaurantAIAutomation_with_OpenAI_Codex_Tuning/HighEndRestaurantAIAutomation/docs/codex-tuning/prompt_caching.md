# Prompt Caching and Cache-Aware Prompt Design

**Purpose:** Documents cache-friendly prompt structure and measurement for OpenAI API calls.

## Cache-aware design

Prompt caching benefits exact prefix matches. Put stable instructions, policy, examples, and tool descriptions first. Put variable user input, retrieved chunks, and request-specific details last.

## What to keep stable

- System instructions.
- Output schema.
- Safety rules.
- Tool descriptions.
- Few-shot examples.
- Restaurant tone and brand rules.

## What to keep variable and late

- User query.
- Retrieved chunks.
- Session state.
- Current date/time.
- Tool results.

## Measurement

Log the `usage` object from OpenAI responses when available, including input tokens, output tokens, cached tokens, latency, model, feature name, and route. Track cache hit rate by feature.

## Common mistakes

- Adding timestamps at the beginning of prompts.
- Randomizing examples or tool order.
- Inserting user-specific data before stable instructions.
- Rewriting the system prompt for every request.
