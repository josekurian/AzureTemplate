# Responsible AI Risk Register

| Risk | Example in restaurant use case | Mitigation | Validation |
|---|---|---|---|
| Hallucinated policy | AI invents cancellation terms | RAG with AI Search; quote source document | Groundedness tests |
| PII leakage | Guest phone/email appears in prompt or logs | Language PII redaction; log scrubbing | Synthetic PII tests |
| Harmful content | User asks for abusive guest message | Content Safety thresholds | Red-team prompts |
| Prompt injection | Uploaded private event doc contains hidden instructions | Prompt Shields document attack detection | Injection test suite |
| Bias / fairness | Differential recommendations based on protected characteristics | Remove protected attributes; evaluate outputs | Fairness review sample |
| Unsafe automation | AI confirms reservation without checking availability | Human-in-loop for confirmations | E2E reservation test |
| Bad translation | Allergy instruction mistranslated | Translator + human review for allergen content | Bilingual spot check |
| Face misuse | VIP recognition without consent | Disable by default; consent workflow; retention limit | Privacy review |
