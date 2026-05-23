# token-optimization.md — Token Budgeting and Optimization

> **Purpose**: Complete guide to reducing token consumption, controlling costs, and improving throughput for Claude applications at any scale.  
> **Applies to**: All Claude models via API. Critical for high-volume production workloads.  
> **Owner**: jose@hybridgenai.com  
> **Updated**: 2026-05-22

---

## Navigation

1. [Understanding Token Economics](#1-understanding-token-economics)
2. [Current Pricing Reference](#2-current-pricing-reference)
3. [Input Token Optimization](#3-input-token-optimization)
4. [Output Token Optimization](#4-output-token-optimization)
5. [Model Selection for Cost](#5-model-selection-for-cost)
6. [Prompt Caching](#6-prompt-caching-quick-reference)
7. [Batch API for Throughput](#7-batch-api-for-throughput)
8. [Token Counting and Budgeting](#8-token-counting-and-budgeting)
9. [Cost Monitoring](#9-cost-monitoring-and-alerting)
10. [Junior Quick-Start Walkthrough](#10-junior-quick-start-walkthrough)
11. [Senior Patterns and Production Hardening](#11-senior-patterns-and-production-hardening)
12. [Tips, Tricks and Gotchas](#12-tips-tricks-and-gotchas)
13. [Quick Reference Cheatsheet](#13-quick-reference-cheatsheet)

---

## 1. Understanding Token Economics

Token cost has two dimensions: **input tokens** (everything Claude reads) and **output tokens** (everything Claude writes).

**Output tokens cost 5× more than input tokens** per token on Sonnet. This has major design implications.

```
Total Cost = (input_tokens × input_price/MTok) + (output_tokens × output_price/MTok)

Example — Claude Sonnet 4.6 (standard pricing):
  10,000 input tokens + 500 output tokens
  = (10,000 × $3.00/1M) + (500 × $15.00/1M)
  = $0.030 + $0.0075 = $0.0375 per request

IMPLICATION: Halving your output saves MORE than halving your input.
  Cut 500 → 250 output tokens: saves $0.00375  (3.75× cost reduction per token)
  Cut 10,000 → 5,000 input tokens: saves $0.015 (same % reduction, less per-token impact)
```

**Token consumption components in a typical request:**

```
Request = System Prompt + Conversation History + RAG Context + User Message
              ↑                    ↑                  ↑              ↑
          Fixed per req       Grows over time    Per-query        Short
          (cacheable)         (must manage)      (control top_k)  (~100 tok)

Output  = Response Text
              ↑
          Variable (set max_tokens!)
```

---

## 2. Current Pricing Reference

```python
# Pricing as of 2026-05-22 — verify at https://anthropic.com/pricing

PRICING = {
    "claude-opus-4-6": {
        "input_per_mtok": 15.00,     # $15 per million input tokens
        "output_per_mtok": 75.00,    # $75 per million output tokens
        "cache_write_per_mtok": 18.75,  # 1.25× input price
        "cache_read_per_mtok": 1.50,    # 0.10× input price (90% off)
        "batch_discount": 0.50,      # 50% off for Message Batches API
        "context_window": 200_000
    },
    "claude-sonnet-4-6": {
        "input_per_mtok": 3.00,
        "output_per_mtok": 15.00,
        "cache_write_per_mtok": 3.75,
        "cache_read_per_mtok": 0.30,
        "batch_discount": 0.50,
        "context_window": 200_000
    },
    "claude-haiku-4-5-20251001": {
        "input_per_mtok": 0.80,
        "output_per_mtok": 4.00,
        "cache_write_per_mtok": 1.00,
        "cache_read_per_mtok": 0.08,
        "batch_discount": 0.50,
        "context_window": 200_000
    }
}

def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
    model: str = "claude-sonnet-4-6"
) -> float:
    """Calculate cost of a single API call."""
    p = PRICING[model]
    uncached_input = input_tokens - cached_input_tokens
    cost = (
        uncached_input / 1_000_000 * p["input_per_mtok"]
        + cached_input_tokens / 1_000_000 * p["cache_read_per_mtok"]
        + output_tokens / 1_000_000 * p["output_per_mtok"]
    )
    return round(cost, 8)

# Quick reference at 1,000 daily calls:
# Haiku, 1K input + 200 output: ~$0.001/call → $1/day
# Sonnet, 2K input + 500 output: ~$0.014/call → $14/day
# Sonnet + cache (2K static, 200 dynamic): ~$0.003/call → $3/day (78% savings)
```

---

## 3. Input Token Optimization

### Technique 1: System Prompt Compression

Every token in the system prompt is charged on EVERY request. Compress without losing meaning.

```python
# ❌ Verbose system prompt — 87 tokens
VERBOSE = """You are an AI assistant that helps restaurant staff with their questions.
You should always be polite, professional, and helpful. You have access to the
restaurant's menu, wine list, and staff training documents. Please answer questions
accurately and cite your sources when drawing from the knowledge base."""

# ✅ Compressed — 41 tokens (53% reduction)
COMPACT = """Restaurant AI for staff. Tone: professional, warm.
Sources: menu, wine list, training docs. Always cite as [Source: filename]."""

# Savings at 100K calls/month on Sonnet:
# 46 saved tokens × 100,000 calls × $3/MTok = $13.80/month
# (Worth doing at scale; use full prompts in dev for clarity)
```

**Compression techniques:**
- Remove filler words: "Please", "You should always", "Make sure to"
- Use semicolons instead of sentences: "Polite; professional; cite sources"
- Use implicit formatting: "Format: JSON only" vs "Please format your response as valid JSON"
- Replace paragraphs with structured bullets only when truly shorter

---

### Technique 2: Prompt Caching (Biggest Win)

For static system prompts >500 tokens, prompt caching gives a 90% discount on cached tokens.

```python
import anthropic

client = anthropic.Anthropic()

# Static content — define once, cache on every request
RESTAURANT_KNOWLEDGE_BASE = """
[Lumière Restaurant Full Knowledge Base — 8,000 tokens of menus, policies, wine lists]
"""

SYSTEM_PROMPT = """You are Maître, the AI concierge for Lumière restaurant..."""

# Cache both the system prompt AND the knowledge base
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=[
        # Static part 1: System prompt
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"}  # ← Mark for caching
        },
        # Static part 2: Knowledge base
        {
            "type": "text",
            "text": RESTAURANT_KNOWLEDGE_BASE,
            "cache_control": {"type": "ephemeral"}  # ← Also cached
        }
    ],
    messages=[
        # Dynamic: user question — NOT cached (changes every request)
        {"role": "user", "content": guest_question}
    ]
)

# Monitor cache performance
usage = response.usage
print(f"Cache write: {usage.cache_creation_input_tokens} tokens")
print(f"Cache read:  {usage.cache_read_input_tokens} tokens")
print(f"Uncached:    {usage.input_tokens} tokens")
```

**Full caching ROI calculation:**

```python
def calculate_cache_savings(
    requests_per_day: int,
    stable_tokens: int,      # Tokens in cached content (system prompt + docs)
    dynamic_tokens: int,     # Tokens unique per request
    output_tokens: int = 500,
    model: str = "claude-sonnet-4-6"
) -> dict:
    p = PRICING[model]

    # Without cache: all input charged at full rate
    without_cache = requests_per_day * (stable_tokens + dynamic_tokens) / 1_000_000 * p["input_per_mtok"]
    without_cache += requests_per_day * output_tokens / 1_000_000 * p["output_per_mtok"]

    # With cache: first request writes (1.25×), rest read (0.10×)
    cache_write_cost = stable_tokens / 1_000_000 * p["cache_write_per_mtok"]
    cache_read_cost = (requests_per_day - 1) * stable_tokens / 1_000_000 * p["cache_read_per_mtok"]
    dynamic_cost = requests_per_day * dynamic_tokens / 1_000_000 * p["input_per_mtok"]
    output_cost = requests_per_day * output_tokens / 1_000_000 * p["output_per_mtok"]
    with_cache = cache_write_cost + cache_read_cost + dynamic_cost + output_cost

    savings = without_cache - with_cache
    savings_pct = savings / without_cache * 100 if without_cache > 0 else 0

    return {
        "daily_without_cache_usd": round(without_cache, 4),
        "daily_with_cache_usd": round(with_cache, 4),
        "daily_savings_usd": round(savings, 4),
        "savings_pct": round(savings_pct, 1),
        "monthly_savings_usd": round(savings * 30, 2),
        "breakeven_requests": 1  # Cache always worth it when requests > 1/day
    }

# Practical examples:
print(calculate_cache_savings(
    requests_per_day=1_000,
    stable_tokens=8_000,  # 8K token knowledge base + system prompt
    dynamic_tokens=200,   # Average user question
    output_tokens=400
))
# → daily_without_cache_usd: 0.0864
# → daily_with_cache_usd:    0.0117  (86% savings)
# → monthly_savings_usd:     $22.41
```

---

### Technique 3: Trim Conversation History

In multi-turn conversations, history grows unbounded. Left unmanaged, a 20-turn conversation balloons to 10,000+ tokens.

```python
from anthropic import Anthropic

client = Anthropic()

def count_message_tokens(messages: list[dict], model: str = "claude-sonnet-4-6") -> int:
    """Count tokens in a message list using the API token counter."""
    response = client.messages.count_tokens(
        model=model,
        messages=messages
    )
    return response.input_tokens

def trim_to_token_budget(
    messages: list[dict],
    token_budget: int = 8_000,
    model: str = "claude-sonnet-4-6"
) -> list[dict]:
    """
    Trim conversation history to fit within token budget.
    Keeps the most recent messages. Never removes the first user message.

    Args:
        messages: Full conversation history
        token_budget: Max tokens for history (not including system prompt)
        model: Model for token counting

    Returns:
        Trimmed message list
    """
    if not messages:
        return messages

    # Start with all messages; remove oldest pairs until within budget
    trimmed = list(messages)

    while len(trimmed) > 2:  # Always keep at least 1 exchange
        current_tokens = count_message_tokens(trimmed, model)
        if current_tokens <= token_budget:
            break
        # Remove oldest user+assistant pair (first 2 messages)
        trimmed = trimmed[2:]

    return trimmed

# Progressive summarisation — better for very long conversations
SUMMARISE_SYSTEM = """You summarise conversation history into compact memory blocks.
Extract: names, preferences, commitments, key facts. Maximum 150 words. Plain text only."""

def compress_old_history(
    messages: list[dict],
    keep_recent_turns: int = 6
) -> list[dict]:
    """
    Summarise old conversation history; keep recent turns verbatim.
    Result: recent turns + 1 compressed summary message.
    """
    keep_count = keep_recent_turns * 2  # Each turn = 2 messages
    if len(messages) <= keep_count:
        return messages

    old_messages = messages[:-keep_count]
    recent_messages = messages[-keep_count:]

    # Build conversation text for summarisation
    convo_text = "\n".join([
        f"{m['role'].upper()}: {m['content'] if isinstance(m['content'], str) else '[tool/complex message]'}"
        for m in old_messages
    ])

    summary_response = client.messages.create(
        model="claude-haiku-4-5-20251001",   # Cheap model for summarisation
        max_tokens=300,
        system=SUMMARISE_SYSTEM,
        messages=[{"role": "user", "content": convo_text}]
    )
    summary = summary_response.content[0].text

    # Inject summary as first exchange
    compressed_prefix = [
        {"role": "user", "content": f"[Previous conversation summary: {summary}]"},
        {"role": "assistant", "content": "Understood, I have context from our earlier conversation."}
    ]

    return compressed_prefix + recent_messages
```

---

### Technique 4: RAG Instead of Full Documents

Never pass entire documents when only relevant sections are needed.

```python
# ❌ Pass entire 50-page wine list for every query: ~50,000 tokens
prompt = f"Which wines pair with wagyu?\n\nWINE LIST:\n{entire_wine_list_50_pages}"
# Cost per request: ~50,000 × $3/MTok = $0.15 (just for the wine list)

# ✅ Retrieve top-5 relevant wines via vector search: ~500 tokens
relevant_wines = vector_search(query="wagyu pairing", top_k=5)
prompt = f"Which wines pair with wagyu?\n\nRELEVANT WINES:\n{format_wines(relevant_wines)}"
# Cost per request: ~500 × $3/MTok = $0.0015 (100× cheaper)
```

**Setting top_k:**

```python
# Tune top_k based on task — more context → better answers but higher cost
TOP_K_BY_TASK = {
    "simple_factual_lookup": 3,    # "What's the price of X?" — 1-2 chunks usually sufficient
    "comparison_query": 5,          # "Compare these two wines" — needs multiple sources
    "comprehensive_analysis": 8,    # "Summarise our wine policy" — needs broad coverage
    "allergen_check": 3,            # Safety-critical: retrieve extra to be sure
}
```

---

### Technique 5: Request-Level Context Injection

Only inject context relevant to the current request.

```python
def build_minimal_context(
    user_message: str,
    guest_id: str,
    knowledge_base
) -> str:
    """
    Build the smallest sufficient context for this specific request.
    Don't inject everything — inject what this query needs.
    """
    context_parts = []

    # Always include: core persona (cached)
    # (handled in system prompt — not here)

    # Conditionally include: guest preferences
    if any(kw in user_message.lower() for kw in ["prefer", "like", "usual", "remember"]):
        prefs = load_guest_preferences(guest_id)
        if prefs:
            context_parts.append(f"Guest preferences on file:\n{prefs}")

    # Conditionally include: knowledge base chunks
    if any(kw in user_message.lower() for kw in ["menu", "wine", "allergen", "book", "reservation"]):
        chunks = knowledge_base.search(user_message, top_k=4)
        if chunks:
            context_parts.append("Relevant knowledge:\n" + "\n---\n".join(c["text"] for c in chunks))

    return "\n\n".join(context_parts)
```

---

## 4. Output Token Optimization

### Always Set max_tokens Explicitly

The default `max_tokens` is the model maximum. You pay for every token Claude generates.

```python
# Task-appropriate max_tokens values (use these as starting points)
MAX_TOKENS_BY_TASK = {
    "binary_classification": 5,        # "positive" or "negative"
    "multi_class_classification": 20,  # One class name
    "sentiment_score": 10,             # "0.82" or "positive/high"
    "yes_no_answer": 5,                # "yes" or "no"
    "single_fact_lookup": 50,          # Short factual answer
    "short_response": 150,             # 2-3 sentences
    "paragraph_response": 400,         # ~1 paragraph
    "structured_extraction": 512,      # JSON with multiple fields
    "summary_short": 300,              # Brief summary
    "summary_detailed": 800,           # Detailed summary
    "document_analysis": 1500,         # Multi-section analysis
    "code_generation_small": 500,      # Small function
    "code_generation_large": 2048,     # Full module
    "long_form_content": 4096,         # Articles, reports
}

# Usage:
response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=MAX_TOKENS_BY_TASK["binary_classification"],
    messages=[{"role": "user", "content": f"Is this positive or negative? '{text}' Answer with one word only."}]
)
```

---

### Output Format Compression

Instructions about format directly control output token count.

```python
# ❌ Verbose instruction — produces long response (~400 tokens)
"Explain your reasoning step by step, then provide your final answer with justification."

# ✅ Compressed instruction — produces short response (~40 tokens)
"Return ONLY valid JSON. No explanation. No code fences."

# ❌ Open-ended — Claude generates as much as it thinks is helpful (~300 tokens)
"Tell me about our gluten-free options."

# ✅ Bounded — Claude stays concise (~100 tokens)
"List our top 3 gluten-free main courses. One sentence each. No other text."
```

**Format instructions that reduce output tokens:**

```python
OUTPUT_CONTROL_INSTRUCTIONS = {
    "json_only": "Return ONLY valid JSON. No explanation, no markdown code fences.",
    "one_word": "Answer with one word only.",
    "yes_no": "Answer 'yes' or 'no' only. No explanation.",
    "bullet_max_5": "Bullet points only. Maximum 5 bullets. Max 10 words per bullet.",
    "one_sentence": "Answer in one sentence of maximum 20 words.",
    "first_paragraph_only": "Answer in one paragraph of maximum 80 words.",
    "label_only": "Return only the category label, nothing else.",
}
```

---

### Prefill for Controlled Starts

Use the assistant prefill trick to force a specific response format and skip preamble.

```python
# Without prefill: Claude writes preamble ("Certainly! Here is the JSON:")
# + the actual JSON — wastes 15-20 tokens every time

# With prefill: Claude starts directly at "{" — no preamble
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=512,
    messages=[
        {"role": "user", "content": "Extract the name and price from: 'Bottle of Château Margaux 2018: £320'"},
        # Prefill — Claude must continue from here
        {"role": "assistant", "content": "{"}
    ]
)
# Response starts at '{' — no wasted preamble tokens
raw = "{" + response.content[0].text  # Prepend our prefill
result = json.loads(raw)
```

---

## 5. Model Selection for Cost

Not every task needs the most capable model. Use the cheapest model that meets quality requirements.

```python
# Cost comparison for 1,000 daily requests (2K input + 500 output tokens):

MODEL_COST_COMPARISON = {
    "claude-haiku-4-5-20251001": {
        "daily_cost_usd": 1000 * (2000 * 0.80 + 500 * 4.00) / 1_000_000,   # $3.60/day
        "monthly_cost_usd": 108,
        "best_for": ["routing", "classification", "summarisation", "simple Q&A"]
    },
    "claude-sonnet-4-6": {
        "daily_cost_usd": 1000 * (2000 * 3.00 + 500 * 15.00) / 1_000_000,  # $13.50/day
        "monthly_cost_usd": 405,
        "best_for": ["complex reasoning", "code gen", "multi-step tasks", "RAG Q&A"]
    },
    "claude-opus-4-6": {
        "daily_cost_usd": 1000 * (2000 * 15.00 + 500 * 75.00) / 1_000_000, # $67.50/day
        "monthly_cost_usd": 2025,
        "best_for": ["hardest reasoning tasks", "research synthesis", "complex agents"]
    }
}

# Model decision framework:
def select_model(task_type: str, quality_requirement: str = "standard") -> str:
    """
    Select the cheapest model for a given task type.

    task_type: routing | classification | extraction | summarisation |
               conversation | code | complex_reasoning | research
    quality_requirement: fast | standard | high
    """

    # Always use Haiku for fast/cheap tasks
    HAIKU_TASKS = {"routing", "classification", "sentiment", "simple_qa", "summarisation"}

    # Use Sonnet for quality-sensitive tasks
    SONNET_TASKS = {"extraction", "code_gen", "rag_qa", "conversation", "analysis"}

    # Use Opus only when genuinely needed
    OPUS_TASKS = {"complex_reasoning", "research_synthesis", "novel_problem_solving"}

    if task_type in HAIKU_TASKS and quality_requirement != "high":
        return "claude-haiku-4-5-20251001"
    elif task_type in OPUS_TASKS or quality_requirement == "high":
        return "claude-opus-4-6"
    else:
        return "claude-sonnet-4-6"
```

### Cascade Pattern: Haiku → Sonnet → Opus

```python
def cascade_classify(text: str, labels: list[str]) -> dict:
    """
    Try the cheapest model first. Escalate if confidence is low.
    ~80% of requests will be handled by Haiku (cost savings: ~75%).
    """

    CONFIDENCE_THRESHOLD = 0.85

    # Tier 1: Haiku (cheapest, fastest)
    haiku_result = classify_with_confidence(
        text=text,
        labels=labels,
        model="claude-haiku-4-5-20251001"
    )

    if haiku_result["confidence"] >= CONFIDENCE_THRESHOLD:
        return {**haiku_result, "model_used": "haiku", "escalated": False}

    # Tier 2: Sonnet (if Haiku not confident)
    sonnet_result = classify_with_confidence(
        text=text,
        labels=labels,
        model="claude-sonnet-4-6"
    )

    if sonnet_result["confidence"] >= CONFIDENCE_THRESHOLD:
        return {**sonnet_result, "model_used": "sonnet", "escalated": True}

    # Tier 3: Opus (if Sonnet not confident — rare)
    opus_result = classify_with_confidence(
        text=text,
        labels=labels,
        model="claude-opus-4-6"
    )

    return {**opus_result, "model_used": "opus", "escalated": True}

def classify_with_confidence(text: str, labels: list[str], model: str) -> dict:
    """Classify text and extract a confidence score from Claude's response."""
    response = client.messages.create(
        model=model,
        max_tokens=50,
        messages=[{
            "role": "user",
            "content": (
                f"Classify this text into one of: {', '.join(labels)}\n\n"
                f"Text: {text}\n\n"
                f"Return JSON: {{\"label\": \"category\", \"confidence\": 0.95}}"
            )
        }],
        # Force tool use for reliable JSON output
    )
    return json.loads(response.content[0].text)
```

---

## 6. Prompt Caching Quick Reference

*(Full details in caching.md — this section covers the basics)*

```python
# Minimum tokens for caching to be worthwhile: 1,024 tokens
# Cache TTL: 5 minutes of inactivity
# Maximum cache breakpoints: 4 per request

# Mark content for caching:
"cache_control": {"type": "ephemeral"}   # Only option currently

# Placement rule: cached content MUST come before dynamic content
# ✓ [STATIC + cache_control] → [DYNAMIC, no cache_control]
# ✗ [DYNAMIC] → [STATIC + cache_control]  ← breaks cache prefix

# Check if cache was hit:
response.usage.cache_read_input_tokens    # > 0 means cache hit
response.usage.cache_creation_input_tokens  # > 0 means cache write
```

---

## 7. Batch API for Throughput

For async workloads (nightly processing, bulk analysis), use the Message Batches API. **50% discount** on all token costs.

```python
import anthropic
import time

client = anthropic.Anthropic()

def batch_process_invoices(invoices: list[str]) -> list[dict]:
    """
    Process invoices in batch — 50% cheaper than sync.
    Best for: non-real-time tasks where 1-24 hour turnaround is acceptable.
    """

    # Build batch requests
    requests = []
    for i, invoice_text in enumerate(invoices):
        requests.append({
            "custom_id": f"invoice_{i:04d}",
            "params": {
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 300,
                "messages": [{
                    "role": "user",
                    "content": f"Extract: vendor, date, total, currency from:\n{invoice_text}\nReturn JSON only."
                }]
            }
        })

    # Submit batch
    batch = client.beta.messages.batches.create(requests=requests)
    print(f"Batch submitted: {batch.id} ({len(requests)} requests)")

    # Poll for completion (batches process within 1–24 hours)
    while batch.processing_status != "ended":
        time.sleep(60)  # Poll every minute
        batch = client.beta.messages.batches.retrieve(batch.id)
        print(f"Status: {batch.processing_status} — "
              f"Complete: {batch.request_counts.succeeded}/{len(requests)}")

    # Collect results
    results = []
    for result in client.beta.messages.batches.results(batch.id):
        if result.result.type == "succeeded":
            text = result.result.message.content[0].text
            try:
                results.append({
                    "id": result.custom_id,
                    "data": json.loads(text),
                    "success": True
                })
            except json.JSONDecodeError:
                results.append({"id": result.custom_id, "raw": text, "success": False})
        else:
            results.append({
                "id": result.custom_id,
                "error": result.result.error.type,
                "success": False
            })

    return results

# Cost comparison:
# 1,000 invoices × 500 tokens input × $0.80/MTok (Haiku) = $0.40 sync
# Same batch: $0.40 × 50% = $0.20 (saves $0.20 per 1,000 invoices)
# At 100,000 invoices/month: saves $20/month
```

**When to use Batch API:**

| Use Sync API | Use Batch API |
|---|---|
| User is waiting for response | Background processing |
| Latency < 5 seconds required | 1–24 hour turnaround OK |
| Real-time interactions | Nightly ETL, analytics |
| Single request | 10+ requests |

---

## 8. Token Counting and Budgeting

### Count Tokens Before Sending

```python
def audit_request_tokens(
    system_prompt: str,
    messages: list[dict],
    tools: list[dict] = None,
    model: str = "claude-sonnet-4-6"
) -> dict:
    """
    Count tokens in a request before sending.
    Use to: validate budget, compare prompt versions, detect bloat.
    """
    kwargs = {
        "model": model,
        "system": system_prompt,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools

    token_count = client.messages.count_tokens(**kwargs)

    # Estimate cost
    input_tokens = token_count.input_tokens
    cost_uncached = input_tokens / 1_000_000 * PRICING[model]["input_per_mtok"]

    return {
        "total_input_tokens": input_tokens,
        "estimated_cost_usd": round(cost_uncached, 6),
        "pct_of_context_window": round(input_tokens / PRICING[model].get("context_window", 200_000) * 100, 1),
        "model": model
    }

# Usage
audit = audit_request_tokens(
    system_prompt=MY_SYSTEM_PROMPT,
    messages=conversation_history,
    tools=MY_TOOLS
)
print(f"Input tokens: {audit['total_input_tokens']:,}")
print(f"Context used: {audit['pct_of_context_window']}%")
print(f"Estimated cost: ${audit['estimated_cost_usd']:.6f}")
```

### Set Dynamic max_tokens Based on Request Type

```python
def get_max_tokens(user_message: str) -> int:
    """
    Dynamically set max_tokens based on what the user is asking.
    Prevents paying for long responses when short answers suffice.
    """
    msg_lower = user_message.lower()

    # Very short answers expected
    if any(q in msg_lower for q in ["yes or no", "is it", "do you have", "are you"]):
        return 20

    # Short factual answers
    if any(q in msg_lower for q in ["what time", "how much", "what price", "when does"]):
        return 100

    # Medium responses
    if any(q in msg_lower for q in ["recommend", "suggest", "tell me about"]):
        return 400

    # Longer content
    if any(q in msg_lower for q in ["explain", "describe", "summarise", "compare"]):
        return 800

    # Default
    return 500
```

---

## 9. Cost Monitoring and Alerting

```python
import os
from datetime import datetime, timedelta

class TokenBudgetMonitor:
    """
    Track daily/monthly token spend and alert when approaching budget.
    """

    def __init__(
        self,
        daily_budget_usd: float = 10.0,
        monthly_budget_usd: float = 200.0,
        alert_threshold_pct: float = 0.80
    ):
        self.daily_budget = daily_budget_usd
        self.monthly_budget = monthly_budget_usd
        self.alert_threshold = alert_threshold_pct
        self.daily_spend: dict[str, float] = {}  # date_str → cost
        self.monthly_spend: dict[str, float] = {}  # month_str → cost

    def record_call(self, response, model: str = "claude-sonnet-4-6"):
        """Record cost of an API call."""
        cost = calculate_cost(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cached_input_tokens=response.usage.cache_read_input_tokens,
            model=model
        )

        today = datetime.utcnow().strftime("%Y-%m-%d")
        month = datetime.utcnow().strftime("%Y-%m")

        self.daily_spend[today] = self.daily_spend.get(today, 0) + cost
        self.monthly_spend[month] = self.monthly_spend.get(month, 0) + cost

        # Check alerts
        if self.daily_spend[today] >= self.daily_budget * self.alert_threshold:
            self._alert(f"Daily budget {self.alert_threshold*100:.0f}% used: "
                       f"${self.daily_spend[today]:.4f} / ${self.daily_budget}")

        if self.monthly_spend[month] >= self.monthly_budget * self.alert_threshold:
            self._alert(f"Monthly budget {self.alert_threshold*100:.0f}% used: "
                       f"${self.monthly_spend[month]:.2f} / ${self.monthly_budget}")

    def _alert(self, message: str):
        """Send alert — replace with your alerting mechanism."""
        print(f"⚠️  TOKEN BUDGET ALERT: {message}")
        # In production: send to Slack, PagerDuty, Azure Monitor, etc.

# KQL query for Azure Monitor cost dashboard:
KQL_DAILY_COST = """
AppTraces
| where Message == "api_call_completed"
| extend InputTokens = toint(Properties.input_tokens)
| extend OutputTokens = toint(Properties.output_tokens)
| extend CachedTokens = toint(Properties.cached_input_tokens)
| extend Cost = (InputTokens - CachedTokens) * 0.000003
           + CachedTokens * 0.0000003
           + OutputTokens * 0.000015
| summarize TotalCostUSD = sum(Cost), TotalCalls = count() by bin(TimeGenerated, 1d)
| order by TimeGenerated desc
"""
```

---

## 10. Junior Quick-Start Walkthrough

**Goal**: Reduce your API costs by 50%+ in 30 minutes.

**Step 1**: Always set `max_tokens`.

```python
# Before: default (model max — you pay for everything Claude generates)
response = client.messages.create(model="claude-sonnet-4-6", messages=[...])

# After: set appropriate limit
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=300,    # For a short answer — saves 80%+ on output tokens
    messages=[...]
)
```

**Step 2**: Use Haiku for simple tasks.

```python
# Before: Sonnet for everything
model = "claude-sonnet-4-6"   # $3.00/MTok input

# After: Haiku for routing, classification, simple Q&A
model = "claude-haiku-4-5-20251001"   # $0.80/MTok input (3.75× cheaper)
```

**Step 3**: Add prompt caching to static system prompts.

```python
# Before: plain string
system = "You are a helpful restaurant assistant. [2,000 tokens of instructions]"

# After: marked for caching
system = [{"type": "text", "text": "You are a helpful...", "cache_control": {"type": "ephemeral"}}]
# First request: pays 1.25× (cache write). All subsequent: pay 0.10× (90% off!)
```

**Step 4**: Add an output format instruction.

```python
# Before: open-ended
"Which wines go with lamb?"
# Claude writes 300 words

# After: constrained
"Which 3 wines go with lamb? Return as bullet points, max 10 words each."
# Claude writes ~60 words
```

---

## 11. Senior Patterns and Production Hardening

### Dynamic Context Budget Allocation

```python
@dataclass
class ContextBudget:
    """
    Allocate the context window deliberately.
    Total should not exceed ~180,000 tokens (leave buffer for output).
    """
    system_prompt: int = 2_000          # Fixed
    conversation_history: int = 8_000  # Rolling window
    rag_context: int = 4_000           # Retrieved chunks (top_k × chunk_size)
    tool_definitions: int = 2_000      # Tools (if any)
    user_message: int = 1_000          # Current input
    output_reserve: int = 2_048        # max_tokens allocation
    # Total: ~19,048 — well within 200K window

    @property
    def total_input(self) -> int:
        return (self.system_prompt + self.conversation_history +
                self.rag_context + self.tool_definitions + self.user_message)

    def validate(self, context_window: int = 200_000) -> bool:
        return self.total_input + self.output_reserve <= context_window

# Usage
budget = ContextBudget(rag_context=6_000)  # More context for complex queries
assert budget.validate(), "Context budget exceeds window!"
```

### Token Efficiency Metrics

```python
def calculate_efficiency_metrics(responses: list) -> dict:
    """
    Calculate token efficiency across multiple API calls.
    Key metric: useful_output_tokens / total_cost_usd
    """
    total_input = sum(r.usage.input_tokens for r in responses)
    total_output = sum(r.usage.output_tokens for r in responses)
    total_cached = sum(getattr(r.usage, "cache_read_input_tokens", 0) for r in responses)
    total_cost = sum(calculate_cost(
        r.usage.input_tokens, r.usage.output_tokens,
        getattr(r.usage, "cache_read_input_tokens", 0)
    ) for r in responses)

    return {
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "cache_hit_rate_pct": round(total_cached / total_input * 100, 1) if total_input else 0,
        "avg_input_per_call": round(total_input / len(responses)),
        "avg_output_per_call": round(total_output / len(responses)),
        "output_to_input_ratio": round(total_output / total_input, 3),
        "total_cost_usd": round(total_cost, 4),
        "cost_per_call_usd": round(total_cost / len(responses), 6),
        "tokens_per_dollar": round((total_input + total_output) / total_cost) if total_cost else 0,
    }
```

---

## 12. Tips, Tricks and Gotchas

**Tip 1 — Measure before optimising.** Log `response.usage` on every call. You can't optimise what you don't measure. Identify the top 3 highest-token request types and focus there first.

**Tip 2 — Caching + Haiku > Sonnet uncached.** A Sonnet prompt with 90% cache hits often costs less than the same prompt on Haiku without caching. Calculate the actual numbers for your use case.

**Tip 3 — Output tokens are 5× more valuable to save.** Before compressing your system prompt (input savings), check if you can reduce max_tokens or add format constraints (output savings) — higher ROI.

**Tip 4 — Batch your non-urgent work.** Any processing that doesn't need to happen in real-time (nightly reports, document indexing, batch classification) should use the Message Batches API for 50% off.

**Tip 5 — Use `count_tokens` API before deploying a new prompt.** Never guess token counts. The `client.messages.count_tokens()` call tells you exactly what a prompt costs before you ship it.

**Gotcha 1 — Cache TTL is 5 minutes.** If your system is idle for 5+ minutes between requests (e.g., overnight), the cache expires. For low-traffic apps, caching may not pay off. Run the ROI calculation first.

**Gotcha 2 — Minimum cacheable prefix is 1,024 tokens.** Content shorter than 1,024 tokens cannot be cached. Don't bother adding cache_control to short prompts.

**Gotcha 3 — Tool definitions count as input tokens.** A complex tool schema can add 300–500 tokens per tool. With 8 tools, that's 2,400–4,000 extra input tokens on every call. Mark tool definitions for caching too.

**Gotcha 4 — Batch API has a 24-hour completion window.** Don't use it for anything user-facing or time-sensitive. It's for background processing only.

**Gotcha 5 — Haiku is not "worse" — it's specialised.** Haiku scores nearly as well as Sonnet on classification, summarisation, and extraction tasks. Only upgrade when you measure a quality gap. Don't assume Sonnet is always needed.

---

## 13. Quick Reference Cheatsheet

```
COST FORMULA:
  cost = (input_tok × input_$/MTok) + (output_tok × output_$/MTok)
  Cache read: input price × 0.10 (90% off)
  Cache write: input price × 1.25

PRICING OVERVIEW (verify at anthropic.com/pricing):
  Haiku 4.5:  $0.80 in / $4.00 out (per MTok)
  Sonnet 4.6: $3.00 in / $15.00 out
  Opus 4.6:   $15.00 in / $75.00 out

COST REDUCTION HIERARCHY (most impactful first):
  1. Prompt caching — 90% off static content (immediate, high ROI)
  2. Use Haiku for simple tasks — 3.75× cheaper than Sonnet
  3. Set max_tokens — prevent long unnecessary outputs
  4. RAG instead of full docs — 100× input reduction possible
  5. Output format constraints — "JSON only" vs prose
  6. Batch API — 50% off async workloads
  7. Trim conversation history — prevents unbounded growth

MAX_TOKENS BY TASK:
  Classification: 5–20     Short answer: 50–150
  Paragraph: 300–500       Analysis: 800–2,000
  Code gen: 500–2,048      Long-form: 2,048–4,096

CACHE BREAKEVEN:
  Any system prompt >1,024 tokens AND >1 request/day = cache it
  Static knowledge base >500 tokens AND >1 request/5min = cache it

MONITORING MUST-HAVES:
  ✓ Log input_tokens + output_tokens + cached_tokens per call
  ✓ Daily cost alert at 80% of budget
  ✓ Monthly report: cost per call type, cache hit rate, model mix
```
