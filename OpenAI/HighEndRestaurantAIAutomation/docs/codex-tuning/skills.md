# Skills and Capability Map

**Purpose:** Defines reusable capabilities and decision patterns that Codex and other agents should apply while building or operating the sample app.

## Skill defaults

```yaml
skill_defaults:
  prefer_specialized_service_when_fit: true
  keep_skills_narrow: true
  document_inputs_outputs_side_effects: true
  test_skills_indirectly_via_workflows: true
```

## Skill: Azure and OpenAI service selection

Use the least complex correct service first.

- Azure AI Language: classification, PII, sentiment, entities
- Azure AI Translator: language conversion
- Azure AI Speech: STT and TTS
- Azure AI Vision: image understanding and OCR-like scenarios from photos
- Document Intelligence: forms and structured docs
- Azure AI Search or OpenAI file/vector search: grounded retrieval
- Azure OpenAI or OpenAI Responses API: generation, synthesis, tool orchestration

## Skill: Retrieval-augmented generation

- chunk semantically
- store metadata
- retrieve broadly, answer narrowly
- cite sources
- refuse unsupported claims

## Skill: Safety-first response generation

- screen risky input
- inspect retrieved documents for injection
- enforce refusal and escalation
- use structured validations for outputs and tool args

## Skill: Multimodal restaurant automation

- use vision for menu images or dining-room image tasks
- use document intelligence for PDFs and supplier forms
- use speech for voice concierge
- use translator for multilingual service
- use generation for explanations and conversations

## Skill: Production readiness

- managed identity
- RBAC
- Key Vault
- observability
- budgets and alerts
- rollback planning
- evals before release

## Codex skill-writing tips

When converting repeated tasks into explicit Codex skills:

- keep the skill focused on one workflow
- include prerequisites
- specify which files or docs to read first
- specify validation expectations
- state what not to do

## Anti-patterns

- giant skills that try to solve every task in one file
- vague skill descriptions without inputs, outputs, or safety rules
- skills that duplicate project-wide instructions instead of extending them
