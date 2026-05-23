# AI-102 Practice Mapping for the Project

**Purpose:** Maps repository patterns to AI-102 study areas while keeping the implementation aligned with modern OpenAI and Codex tuning practices.

## Service mapping defaults

| Need | Preferred service | Default reason |
| --- | --- | --- |
| conversational generation | Azure OpenAI / OpenAI Responses API | strongest general language reasoning |
| retrieval over documents | Azure AI Search or OpenAI file/vector search depending architecture | authoritative grounding |
| embeddings | `text-embedding-3-large` or `text-embedding-3-small` | quality vs cost choice |
| safety classification | Azure AI Content Safety plus prompt policy | early blocking and traceability |
| translation | Azure AI Translator | cheaper and more deterministic than LLM translation |
| speech | Azure AI Speech | native STT and TTS |
| OCR/form extraction | Azure AI Document Intelligence | structured extraction beats prompt parsing |
| image analysis | Azure AI Vision | efficient deterministic image services |

## AI-102 study map

### Plan and manage an Azure AI solution

Repository practice:

- choose between deterministic AI services and LLM reasoning
- document deployment names and endpoint purpose
- define eval gates before promoting prompt or model changes

Recommended default values:

```yaml
environment_strategy:
  dev: isolated deployments
  staging: production-like with safe datasets
  prod: locked prompts and gated rollouts
```

### Implement generative AI solutions

Repository practice:

- use Responses API for new work
- use JSON Schema structured outputs
- use `previous_response_id` for multi-turn state
- keep tools explicit and permission-scoped

### Implement knowledge mining and document solutions

Repository practice:

- chunk by semantic units
- keep metadata for date, audience, and confidentiality
- re-evaluate retrieval after every schema change

### Implement content safety and responsible AI

Repository practice:

- classify risky content before expensive generation
- use refusal and escalation rules
- log safety blocks with categories and severity

### Deploy and monitor Azure AI solutions

Repository practice:

- CI/CD gates for prompts, model configs, and indexes
- dashboards for latency, 429s, cost, and safety block rates
- rollback path for prompts and model deployments

## Suggested study-to-implementation checklist

- Can this use a deterministic Azure service instead of an LLM?
- If LLMs are needed, is the task grounded with retrieval or tool results?
- Are structured outputs used where machines consume the answer?
- Are safety and PII rules checked before release?
- Can the deployment be rolled back without data loss or downtime?

## Tips

- AI-102 questions often test service selection, not just prompt quality.
- For extraction, classification, translation, OCR, and speech, assume a specialized Azure service may be the correct first answer.
- For enterprise deployments, expect identity, RBAC, Key Vault, and monitoring to matter as much as the model itself.
