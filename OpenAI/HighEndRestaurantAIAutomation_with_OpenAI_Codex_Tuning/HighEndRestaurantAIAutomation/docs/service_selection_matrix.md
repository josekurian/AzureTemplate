# Service Selection Matrix

| Requirement | Correct service | Avoid this distractor | Reason |
|---|---|---|---|
| Generate concierge response | Azure OpenAI | Azure AI Language | Language analyzes text; it does not generate hospitality prose. |
| Retrieve restaurant policies | Azure AI Search | Azure OpenAI alone | Search grounds answers in approved content. |
| Translate menu/policy | Azure Translator | Azure AI Language | Translator is designed for translation. |
| Redact PII | Azure AI Language | GPT prompt only | PII detection is deterministic and auditable. |
| Extract invoice fields | Document Intelligence | Vision OCR | Document Intelligence returns structured fields. |
| Analyze plating photo | Azure AI Vision / Custom Vision | Document Intelligence | Vision handles images and visual quality. |
| Voice reservations | Azure Speech | Azure OpenAI text model | Speech handles STT/TTS. |
| Detect jailbreaks in prompts/docs | Content Safety Prompt Shields | Simple regex | Prompt Shields are designed for prompt attacks and document attacks. |
| Search large knowledge base | AI Search | Cosmos DB query alone | Search provides ranking, semantic, and vector retrieval. |
| Omnichannel bot | Azure Bot Service | Custom channel code only | Bot Service manages channels and bot lifecycle. |
