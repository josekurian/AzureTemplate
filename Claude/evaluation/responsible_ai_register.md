# Responsible AI Risk Register
## Restaurant AI Assistant — Lumière

> AI-102 Exam: This document represents the governance artefact for the Responsible AI
> section of the exam. Every identified risk maps to one of the six Microsoft RAI principles.

---

## Project Details

| Field | Value |
|-------|-------|
| Project | Lumière Restaurant AI Assistant |
| Owner | Jose Kurian — jose@hybridgenai.com |
| Review Date | 2026-05-22 |
| Deployment Scope | Guest-facing chatbot + Staff knowledge assistant |
| Azure Region | East US |

---

## Six Responsible AI Principles — Applied

### 1. Fairness
**Risk**: Model may give inconsistent advice based on implied guest characteristics in the prompt.  
**Mitigation**: System prompt instructs equal service to all guests. Evaluation dataset includes diverse persona queries.  
**Test**: Monthly fairness evaluation using demographic parity check on recommendation quality.  
**Status**: ✅ Implemented

### 2. Reliability & Safety
**Risk**: Model returns hallucinated menu items, allergens, or wine vintages not in the knowledge base.  
**Mitigation**: RAG grounding with AI Search; groundedness detection in evaluation pipeline; system prompt instructs model to cite sources.  
**Test**: Automated groundedness scoring on 100 Q&A pairs monthly. Threshold: ≥ 0.85.  
**Status**: ✅ Implemented

### 3. Privacy & Security
**Risk**: Guest names or dietary restrictions appear in model prompts and are logged.  
**Mitigation**: PII detection (Azure AI Language) strips names before logging. Diagnostic Settings exclude request/response body for GDPR compliance.  
**Test**: Privacy scan on log samples monthly.  
**Status**: ✅ Implemented

### 4. Inclusiveness
**Risk**: Voice interface inaccessible to guests with speech or hearing differences.  
**Mitigation**: Text fallback always available; speech model tuned for diverse accents; multi-language via Translator.  
**Test**: Accessibility audit quarterly using WCAG 2.1 AA criteria.  
**Status**: 🔄 In Progress

### 5. Transparency
**Risk**: Guests do not know they are interacting with an AI.  
**Mitigation**: Clear AI disclosure banner in UI: "Powered by Lumière AI Assistant". System prompt prohibits impersonating a human server.  
**Test**: UI review on every deployment.  
**Status**: ✅ Implemented

### 6. Accountability
**Risk**: Unclear who is responsible when the AI gives incorrect allergy information.  
**Mitigation**: Human-in-the-loop for allergy queries — AI prefixes all allergy responses with "Please confirm with your server before ordering." Audit trail in Log Analytics.  
**Test**: Quarterly review of allergy-related interactions by Head of Operations.  
**Status**: ✅ Implemented

---

## Specific Risk Register

| # | Risk | RAI Principle | Likelihood | Impact | Mitigation | Evidence | Rollback |
|---|------|---------------|------------|--------|------------|----------|----------|
| R1 | Harmful content in model response | Safety | Low | High | Azure OpenAI content filters + Content Safety post-processing | Filter config in openai.bicep | Disable AI endpoint; serve static FAQ |
| R2 | Jailbreak bypasses safety controls | Safety | Medium | High | Prompt Shields (user prompt attack detection) | Shield trigger rate monitored daily | Block user session; alert security team |
| R3 | Document injection in supplier PDFs | Safety | Medium | High | Prompt Shields document attack detection | Tested with 20 adversarial PDFs | Remove document from search index |
| R4 | Incorrect allergen information | Reliability | Low | Critical | Human-in-the-loop disclaimer on all allergen responses | QA evaluation dataset with allergen queries | Disable AI for allergen queries; use static menu |
| R5 | Guest PII in audit logs | Privacy | Low | High | PII detection before logging | Privacy scan results | Purge affected log entries; notify DPO |
| R6 | Biased wine recommendations | Fairness | Low | Medium | Diverse evaluation dataset; monthly fairness review | Evaluation report v1.0 | Prompt update; re-evaluation required |
| R7 | AI impersonating human staff | Transparency | Low | Medium | System prompt prohibition + UI disclosure | Prompt version control | Immediate prompt rollback |
| R8 | No audit trail for AI decisions | Accountability | Low | High | Application Insights + Log Analytics full trace | KQL dashboard operational | N/A — monitoring always on |

---

## Incident Response Procedure

1. **Detection**: Alert fires in Azure Monitor (content safety block spike, hallucination report from staff)
2. **Triage** (< 15 min): On-call engineer assesses severity using Responsible AI Risk Register
3. **Contain** (< 30 min): Rollback to previous container revision OR disable AI endpoint
4. **Communicate** (< 1 hour): Notify affected guests if applicable; log incident
5. **Root Cause** (< 48 hours): Review Application Insights traces; update risk register
6. **Remediate**: Prompt update + evaluation gate + re-deployment via CI/CD
7. **Review**: Post-incident review within 7 days; update this register

---

## Model Approval Record

| Deployment | Model | Approved By | Date | Evaluation Score | Notes |
|------------|-------|-------------|------|-----------------|-------|
| gpt-4o-chat-v1 | gpt-4o (2024-08-06) | Jose Kurian | 2026-05-22 | Groundedness: 0.91, Relevance: 0.88 | Initial production deployment |
