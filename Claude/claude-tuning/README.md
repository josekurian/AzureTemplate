# Claude Tuning Guide — Index

> Complete reference library for optimising, tuning, and productionising Claude AI applications.  
> **Owner**: jose@hybridgenai.com | **Last Updated**: 2026-05-22  
> **Current Claude models**: claude-opus-4-6 | claude-sonnet-4-6 | claude-haiku-4-5-20251001

---

## How to Use This Library

Each file in this library is a self-contained, comprehensive reference on one topic. All files follow the same structure:

- **Navigation** — jump to any section
- **Who This Is For** — junior vs senior reading paths
- **Numbered sections** — concepts, code, defaults, options explained
- **Junior Developer Walkthrough** — step-by-step for beginners
- **Senior Developer Patterns** — production-grade patterns
- **Tips, Tricks, and Gotchas** — hard-won lessons
- **Quick Reference Cheatsheet** — copy-paste ready code

Every code example uses **Lumière**, a fine dining restaurant, as the concrete domain. This keeps examples realistic and consistent across all files.

---

## File Index

| # | File | Topic | Size | Priority |
|---|------|--------|------|----------|
| 1 | [prompts.md](prompts.md) | Prompt engineering: XML tags, examples, chain-of-thought, anti-patterns | ~44KB | ⭐ Essential |
| 2 | [system-prompts.md](system-prompts.md) | System prompt structure, versioning, testing, templates | ~52KB | ⭐ Essential |
| 3 | [token-optimization.md](token-optimization.md) | Token budgeting, caching, model selection for cost | ~36KB | ⭐ Essential |
| 4 | [memory-management.md](memory-management.md) | Context window, conversation history, external memory | ~44KB | ⭐ Essential |
| 5 | [agents.md](agents.md) | Agent loops, orchestration, tool design, reliability | ~48KB | ⭐ Essential |
| 6 | [tool-use.md](tool-use.md) | Function calling, schemas, error handling in tools | ~44KB | ⭐ Essential |
| 7 | [safety-guidelines.md](safety-guidelines.md) | Guardrails, jailbreak detection, PII, responsible AI | ~60KB | ⭐ Essential |
| 8 | [performance-tuning.md](performance-tuning.md) | Latency, TTFT, streaming, parallelism, caching | ~56KB | High |
| 9 | [caching.md](caching.md) | Prompt caching deep dive, ROI calculation, warming | ~36KB | High |
| 10 | [error-handling.md](error-handling.md) | Retries, fallbacks, timeouts, graceful degradation | ~52KB | High |
| 11 | [rag-patterns.md](rag-patterns.md) | RAG pipeline, chunking, hybrid search, groundedness | ~44KB | High |
| 12 | [evaluation.md](evaluation.md) | LLM-as-judge, eval datasets, CI/CD quality gates | ~40KB | High |
| 13 | [model-selection.md](model-selection.md) | Opus vs Sonnet vs Haiku decision framework | ~44KB | High |
| 14 | [streaming.md](streaming.md) | SSE streaming, async, WebSocket, tool-use streaming | ~52KB | Medium |
| 15 | [context-management.md](context-management.md) | Context budget planning, map-reduce, dynamic injection | ~52KB | Medium |
| 16 | [structured-output.md](structured-output.md) | JSON extraction, Pydantic, prefill, robust parsing | ~32KB | Medium |
| 17 | [multimodal.md](multimodal.md) | Vision, image analysis, OCR, multi-image patterns | ~44KB | Medium |
| 18 | [cost-optimization.md](cost-optimization.md) | Cost drivers, budget monitoring, ROI strategies | ~48KB | Medium |
| 19 | [batch-processing.md](batch-processing.md) | Message Batches API, async processing, 50% discount | ~60KB | Medium |
| 20 | [fine-tuning.md](fine-tuning.md) | When to fine-tune vs prompt-engineer vs RAG | ~56KB | Reference |
| 21 | [skills.md](skills.md) | Claude's skill-use patterns and capability overview | ~8KB | Reference |

**Total library size**: ~25,500 lines / ~970KB

---

## Quick Start by Goal

### Reduce Costs
```
1. model-selection.md  → Choose cheapest model per task
2. caching.md          → Cache expensive prompts (save 90%)
3. token-optimization.md → Trim tokens, right-size max_tokens
4. cost-optimization.md  → Budget tracking, batch API (50% off)
5. batch-processing.md   → Async workloads at half the price
```

### Improve Accuracy
```
1. prompts.md           → XML structure, few-shot, chain-of-thought
2. system-prompts.md    → Well-crafted constraints and personas
3. rag-patterns.md      → Inject fresh domain knowledge
4. structured-output.md → Reliable JSON with Pydantic validation
5. evaluation.md        → Measure quality objectively
```

### Build Agents
```
1. agents.md           → Agent loop design, orchestration
2. tool-use.md         → Tool schemas, parallel tools, error handling
3. memory-management.md → Conversation history, external memory
4. error-handling.md   → Retries, fallbacks, circuit breakers
5. context-management.md → Keep context window healthy
```

### Production Reliability
```
1. error-handling.md     → Retries, fallbacks, circuit breaker
2. performance-tuning.md → TTFT, streaming, parallelism, caching
3. streaming.md          → SSE, WebSocket, React integration
4. safety-guidelines.md  → Guardrails, jailbreak detection, audit logging
```

### Handle Multimodal / Vision
```
1. multimodal.md        → Image analysis, OCR, token costs
2. rag-patterns.md      → Multimodal RAG with Azure AI Search
3. batch-processing.md  → Batch image analysis at 50% cost
```

### Get Structured Output
```
1. structured-output.md → JSON schema, prefill, Pydantic
2. tool-use.md          → Use tools for guaranteed structure
3. prompts.md           → Prompt techniques for format compliance
```

### Go to Production Safely
```
1. safety-guidelines.md  → 5-layer safety architecture
2. error-handling.md     → Graceful degradation
3. evaluation.md         → Quality gates in CI/CD
4. cost-optimization.md  → Budget governance
5. model-selection.md    → Right model per environment
```

---

## Model Quick Reference (2026)

| Model | Best For | Input | Output | Context |
|-------|---------|-------|--------|---------|
| claude-haiku-4-5-20251001 | Classification, extraction, routing, simple Q&A | $0.80/MTok | $4.00/MTok | 200K |
| claude-sonnet-4-6 | RAG, analysis, coding, most production tasks | $3.00/MTok | $15.00/MTok | 200K |
| claude-opus-4-6 | Complex reasoning, agentic tasks, research | $15.00/MTok | $75.00/MTok | 200K |

**Batch API discount**: 50% off all models for async workloads  
**Prompt cache read**: 10% of input price (cache write: 125% of input price, one-time)  
**Min cache block size**: 1,024 tokens  

---

## Key Default Values Reference

These defaults appear throughout the library. Use them as your starting point:

### API Parameters
```python
# Temperature
temperature=0.0   # Extraction, JSON, classification (deterministic)
temperature=0.3   # Q&A, summaries (slight variety)
temperature=0.7   # Creative writing, descriptions (natural variety)
temperature=1.0   # Brainstorming (maximum creativity)

# Max tokens by task
MAX_TOKENS = {
    "yes_no":           5,      # "yes" or "no"
    "binary_flag":      5,      # True/False
    "classify":         10,     # Single label
    "rag_answer":       600,    # Factual answer with context
    "chat_response":    800,    # Conversational reply
    "summary":          300,    # Document summary
    "extraction":       400,    # Structured data extraction
    "complex_analysis": 4096,   # Deep analysis, long reasoning
    "creative":         2048,   # Creative writing
}
```

### Retry Configuration
```python
RETRY_CONFIG = {
    "max_retries": 3,
    "base_delay_seconds": 1.0,
    "max_delay_seconds": 60.0,
    "backoff_multiplier": 2.0,
    "jitter": True,
    "retryable_status_codes": {429, 500, 529},
}
```

### Context Budget Targets
```python
CONTEXT_TARGETS = {
    "chat":     {"max_tokens": 15_000, "system": 1_000, "history": 8_000, "user": 1_000, "rag": 5_000},
    "rag":      {"max_tokens": 20_000, "system": 2_000, "history": 3_000, "user": 500,   "rag": 14_500},
    "agent":    {"max_tokens": 30_000, "system": 3_000, "history": 10_000, "user": 2_000, "tools": 15_000},
}
```

### Safety Thresholds
```python
CONTENT_SAFETY_THRESHOLDS = {
    "hate":      4,   # Block medium severity and above
    "violence":  4,
    "sexual":    2,   # Strict for public-facing apps
    "self_harm": 2,   # Always strict
}
```

### Batch API
```python
BATCH_CONFIG = {
    "max_requests_per_batch": 10_000,
    "batch_discount": 0.50,      # 50% off all models
    "results_available_days": 29,
    "expires_after_hours": 24,
    "min_poll_interval_seconds": 10,
    "recommended_poll_interval_overnight": 300,  # 5 minutes
}
```

---

## Architecture Patterns Reference

### Model Routing by Task (copy this)
```python
TASK_MODEL_MAP = {
    # High-volume, simple → Haiku
    "classify_intent":     ("claude-haiku-4-5-20251001", 10),
    "sentiment_analysis":  ("claude-haiku-4-5-20251001", 5),
    "extract_entities":    ("claude-haiku-4-5-20251001", 300),
    "yes_no_question":     ("claude-haiku-4-5-20251001", 5),
    "route_request":       ("claude-haiku-4-5-20251001", 20),
    
    # Medium complexity → Sonnet (most production tasks)
    "rag_answer":          ("claude-sonnet-4-6", 600),
    "chat_response":       ("claude-sonnet-4-6", 800),
    "code_generation":     ("claude-sonnet-4-6", 2048),
    "document_analysis":   ("claude-sonnet-4-6", 1500),
    "wine_pairing":        ("claude-sonnet-4-6", 500),
    "menu_description":    ("claude-sonnet-4-6", 200),
    "allergen_query":      ("claude-sonnet-4-6", 400),   # Safety → Sonnet
    
    # Complex reasoning → Opus
    "complex_analysis":    ("claude-opus-4-6", 4096),
    "agentic_task":        ("claude-opus-4-6", 4096),
    "strategic_planning":  ("claude-opus-4-6", 2048),
}

# Environment variable overrides for all tasks
# CLAUDE_MODEL_<TASK_UPPER> = model string
# e.g., CLAUDE_MODEL_CHAT_RESPONSE=claude-haiku-4-5-20251001
```

### Three-Tier Fallback Pattern
```python
# Primary → Fallback → Static
# claude-sonnet-4-6 → claude-haiku-4-5-20251001 → Hard-coded responses
# Covered in: error-handling.md, model-selection.md
```

### Cascade Pattern
```python
# Haiku (fast) → if uncertain → Sonnet → if uncertain → Opus
# Confidence threshold: Haiku ≥ 0.90, Sonnet ≥ 0.85
# Covered in: model-selection.md, performance-tuning.md
```

---

## Environment Variables Reference

All configuration should be overridable via environment variables for different environments (dev/staging/prod).

```bash
# API Configuration
ANTHROPIC_API_KEY=sk-ant-...                  # Required
ANTHROPIC_BASE_URL=https://api.anthropic.com  # Optional override

# Model Selection (override per task for cost control)
CLAUDE_MODEL_CHAT=claude-sonnet-4-6
CLAUDE_MODEL_EXTRACT=claude-haiku-4-5-20251001
CLAUDE_MODEL_COMPLEX=claude-opus-4-6
CLAUDE_COST_MODE=balanced                     # economy | balanced | quality

# Performance
CLAUDE_MAX_CONCURRENT=5                       # Concurrent requests
CLAUDE_REQUEST_TIMEOUT=30                     # Seconds
CLAUDE_STREAM_TIMEOUT=10                      # SSE stream timeout

# Caching
CLAUDE_CACHE_TTL_SECONDS=3600                # Response cache TTL
CLAUDE_CACHE_MAX_SIZE=1000                   # LRU cache size
REDIS_URL=redis://localhost:6379             # Redis for distributed cache

# Azure Integration
AZURE_CONTENT_SAFETY_ENDPOINT=https://...
AZURE_TEXT_ANALYTICS_ENDPOINT=https://...
AZURE_AI_SEARCH_ENDPOINT=https://...
AZURE_AI_SEARCH_KEY=...
APPLICATIONINSIGHTS_CONNECTION_STRING=...

# Budget Controls
CLAUDE_DAILY_BUDGET_USD=50.00               # Daily spend limit
CLAUDE_BUDGET_WARN_THRESHOLD=0.70           # Warn at 70% of budget
CLAUDE_BUDGET_BLOCK_THRESHOLD=1.00          # Block at 100%

# Safety
CLAUDE_CONTENT_SAFETY_HATE_THRESHOLD=4      # 0-6 severity scale
CLAUDE_CONTENT_SAFETY_SEXUAL_THRESHOLD=2
CLAUDE_MAX_INPUT_LENGTH=4000                # Characters
```

---

## Reading Paths by Role

### Junior Developer (new to Claude API)
Start here and read in order:
1. **prompts.md** — Learn the fundamentals (XML tags, few-shot, chain-of-thought)
2. **system-prompts.md** — Write your first production system prompt
3. **model-selection.md** — Understand which model to use when
4. **error-handling.md** — Handle failures gracefully from day one
5. **safety-guidelines.md** — Essential for any public-facing application
6. **structured-output.md** — Extract structured data reliably

### Mid-level Developer (has used Claude, building production systems)
1. **performance-tuning.md** — Optimize latency and throughput
2. **caching.md** — Dramatically reduce costs with prompt caching
3. **rag-patterns.md** — Add domain knowledge reliably
4. **context-management.md** — Handle long conversations at scale
5. **agents.md** — Build autonomous agents
6. **evaluation.md** — Measure and improve quality systematically

### Senior Developer (building enterprise Claude systems)
1. **cost-optimization.md** — Governance, budget controls, ROI analysis
2. **batch-processing.md** — Async pipelines at 50% cost
3. **streaming.md** — Production streaming with SSE and WebSocket
4. **multimodal.md** — Vision, OCR, Azure Document Intelligence routing
5. **fine-tuning.md** — When to fine-tune and how to evaluate
6. **safety-guidelines.md** → Red-team testing and incident response sections

---

## Common Mistakes and Their Solutions

| Mistake | Symptom | Fix | File |
|---------|---------|-----|------|
| Using Opus for everything | High costs, slow responses | TASK_MODEL_MAP routing | model-selection.md |
| No retry logic | 429/500 errors crash app | Exponential backoff | error-handling.md |
| Logging raw user messages | GDPR violation risk | PII redaction before log | safety-guidelines.md |
| max_tokens=2048 for classification | 4× overspend on output | MAX_TOKENS_BY_TASK | cost-optimization.md |
| Streaming without error handling | Silent failures | robust_stream_handler() | streaming.md |
| No cache control on stable prompts | Paying full price every call | cache_control block | caching.md |
| Polling batch every 5 seconds | Rate limit exhaustion | Exponential backoff polling | batch-processing.md |
| No eval set before fine-tuning | Can't measure improvement | Build eval first | fine-tuning.md |
| RAG without re-ranking | Poor retrieval quality | Azure semantic ranker | rag-patterns.md |
| No output safety check | Claude can be manipulated | 5-layer safety pipeline | safety-guidelines.md |
| Context window overflow on agent | Task fails after 20+ turns | ProgressiveSummarizer | context-management.md |
| Blocking main thread with sync | Slow API | AsyncAnthropic client | performance-tuning.md |

---

## File Health Status

All 20 topic files have been expanded from ~5-7KB originals to comprehensive 32-60KB references.

| File | Original | Expanded | Sections |
|------|---------|---------|----------|
| prompts.md | ~7KB | ~44KB | 14 sections + cheatsheet |
| system-prompts.md | ~6KB | ~52KB | 13 sections + cheatsheet |
| token-optimization.md | ~6KB | ~36KB | 13 sections + cheatsheet |
| memory-management.md | ~6KB | ~44KB | 13 sections + cheatsheet |
| agents.md | ~7KB | ~48KB | 14 sections + cheatsheet |
| tool-use.md | ~6KB | ~44KB | 14 sections + cheatsheet |
| safety-guidelines.md | ~5KB | ~60KB | 16 sections + cheatsheet |
| performance-tuning.md | ~6KB | ~56KB | 14 sections + cheatsheet |
| caching.md | ~6KB | ~36KB | 13 sections + cheatsheet |
| error-handling.md | ~7KB | ~52KB | 13 sections + cheatsheet |
| rag-patterns.md | ~6KB | ~44KB | 13 sections + cheatsheet |
| evaluation.md | ~6KB | ~40KB | 13 sections + cheatsheet |
| model-selection.md | ~6KB | ~44KB | 13 sections + cheatsheet |
| streaming.md | ~5KB | ~52KB | 15 sections + cheatsheet |
| context-management.md | ~7KB | ~52KB | 13 sections + cheatsheet |
| structured-output.md | ~6KB | ~32KB | 13 sections + cheatsheet |
| multimodal.md | ~7KB | ~44KB | 14 sections + cheatsheet |
| cost-optimization.md | ~6KB | ~48KB | 16 sections + cheatsheet |
| batch-processing.md | ~6KB | ~60KB | 16 sections + cheatsheet |
| fine-tuning.md | ~6KB | ~56KB | 16 sections + cheatsheet |

---

## Related Files in This Project

```
/Users/josekurian/AzureTemplate/Claude/
├── claude-tuning/          ← You are here
│   ├── README.md           ← This file
│   ├── prompts.md
│   ├── system-prompts.md
│   └── ... (20 topic files)
├── iac/                    ← Azure Bicep IaC templates
├── app/                    ← Python application code
├── .github/workflows/      ← CI/CD pipelines
└── docs/                   ← Implementation plans and guides
```
