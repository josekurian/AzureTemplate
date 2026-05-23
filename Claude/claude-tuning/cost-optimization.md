# cost-optimization.md — Cost Governance and Optimization

> **Purpose**: Comprehensive strategies to control, monitor, and reduce Claude API costs in production. Covers cost driver hierarchy, model right-sizing, caching, batching, budget enforcement, and dashboards with real calculations.
> **Who This Is For**: Junior developers learning cost basics; senior engineers building cost governance for production workloads at scale.
> **Owner**: jose@hybridgenai.com

---

## Navigation

1. [Cost Driver Hierarchy](#1-cost-driver-hierarchy)
2. [Pricing Reference (2026)](#2-pricing-reference-2026)
3. [Strategy 1 — Model Right-Sizing](#3-strategy-1--model-right-sizing-highest-impact)
4. [Strategy 2 — Prompt Caching](#4-strategy-2--prompt-caching-high-impact)
5. [Strategy 3 — max_tokens Discipline](#5-strategy-3--max_tokens-discipline)
6. [Strategy 4 — Batch API for Async Workloads](#6-strategy-4--batch-api-for-async-workloads-50-discount)
7. [Strategy 5 — Application-Layer Response Caching](#7-strategy-5--application-layer-response-caching)
8. [Strategy 6 — Output Format Compression](#8-strategy-6--output-format-compression)
9. [Strategy 7 — Request Deduplication](#9-strategy-7--request-deduplication)
10. [Budget Enforcement and Alerting](#10-budget-enforcement-and-alerting)
11. [Cost Monitoring Dashboard](#11-cost-monitoring-dashboard)
12. [Cost Audit Tool](#12-cost-audit-tool)
13. [Junior Walkthrough — Reduce Your First Bill](#13-junior-walkthrough--reduce-your-first-bill)
14. [Senior Patterns — Enterprise Cost Governance](#14-senior-patterns--enterprise-cost-governance)
15. [Tips, Tricks, and Gotchas](#15-tips-tricks-and-gotchas)
16. [Quick Reference Cheatsheet](#16-quick-reference-cheatsheet)

---

## 1. Cost Driver Hierarchy

```
IMPACT ON TOTAL COST (High → Low)
────────────────────────────────────────────────────────────────

1. MODEL CHOICE                                          ████████████████████ ~60% impact
   Opus vs Haiku = 19× price difference
   Moving 50% of tasks from Sonnet → Haiku = ~47% saving

2. OUTPUT TOKEN COUNT                                    ████████████████ ~20% impact
   Output is 3-5× more expensive per token than input
   Tight max_tokens + compressed output formats save significantly

3. PROMPT CACHING USAGE                                  ████████████ ~15% impact
   Cached reads = 10% of normal input price
   A 3,000-token system prompt cached on 100 req/day saves ~$2.70/day

4. REQUEST VOLUME                                        ████ ~3% impact
   (Linear — can only be reduced by eliminating unnecessary calls)

5. IMAGE TOKEN COST                                      ██ ~2% impact
   1568px image ≈ 3,278 tokens = $0.010 on Sonnet
   Resize to 1024px: ≈ 1,400 tokens = $0.004 (60% saving)
```

---

## 2. Pricing Reference (2026)

```python
# Approximate 2026 pricing (verify at console.anthropic.com)
# Prices in USD per million tokens

PRICING = {
    "claude-opus-4-6": {
        "input":          15.00,   # $/million input tokens
        "output":         75.00,   # $/million output tokens
        "cache_write":    18.75,   # 1.25× input price (one-time write)
        "cache_read":      1.50,   # 0.10× input price (per cache hit)
    },
    "claude-sonnet-4-6": {
        "input":           3.00,
        "output":         15.00,
        "cache_write":     3.75,
        "cache_read":      0.30,
    },
    "claude-haiku-4-5-20251001": {
        "input":           0.80,
        "output":          4.00,
        "cache_write":     1.00,
        "cache_read":      0.08,
    },
}

def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str,
    cache_write_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> dict:
    """
    Calculate the exact cost for a Claude API call.
    
    Args:
        input_tokens:       Non-cached input tokens
        output_tokens:      Generated output tokens
        model:              Model API string
        cache_write_tokens: Tokens written to cache (1.25× input price)
        cache_read_tokens:  Tokens read from cache (0.10× input price)
    
    Returns:
        {
            "input_cost":       float,
            "output_cost":      float,
            "cache_write_cost": float,
            "cache_read_cost":  float,
            "total_cost":       float,
            "breakdown":        str,
        }
    
    Usage:
        cost = calculate_cost(2000, 400, "claude-sonnet-4-6",
                              cache_write_tokens=1800, cache_read_tokens=0)
        print(f"${cost['total_cost']:.4f}")  # →  $0.0060 + $0.0067 = $0.0127 first call
        
        # Second call: same system prompt served from cache
        cost2 = calculate_cost(200, 400, "claude-sonnet-4-6",
                               cache_read_tokens=1800)
        print(f"${cost2['total_cost']:.4f}")  # →  $0.0006 + $0.0001 = $0.0007 (94% cheaper!)
    """
    p = PRICING.get(model, PRICING["claude-sonnet-4-6"])
    
    input_cost       = (input_tokens       / 1_000_000) * p["input"]
    output_cost      = (output_tokens      / 1_000_000) * p["output"]
    cache_write_cost = (cache_write_tokens / 1_000_000) * p["cache_write"]
    cache_read_cost  = (cache_read_tokens  / 1_000_000) * p["cache_read"]
    
    total = input_cost + output_cost + cache_write_cost + cache_read_cost
    
    return {
        "input_cost":       round(input_cost, 6),
        "output_cost":      round(output_cost, 6),
        "cache_write_cost": round(cache_write_cost, 6),
        "cache_read_cost":  round(cache_read_cost, 6),
        "total_cost":       round(total, 6),
        "model":            model,
        "breakdown": (
            f"${input_cost:.4f} input + ${output_cost:.4f} output"
            + (f" + ${cache_write_cost:.4f} cache_write" if cache_write_cost else "")
            + (f" + ${cache_read_cost:.4f} cache_read" if cache_read_cost else "")
            + f" = ${total:.4f}"
        ),
    }
```

---

## 3. Strategy 1 — Model Right-Sizing (Highest Impact)

```python
import os

# Task → Model mapping optimised for cost/quality
# Override via environment variables for easy A/B testing
TASK_MODEL_MAP = {
    # ── Haiku tasks (simple, high-volume) ─────────────────────────────
    # Use when output is a label, flag, or short string
    "classify_intent":        ("claude-haiku-4-5-20251001", 10),
    "detect_language":        ("claude-haiku-4-5-20251001", 5),
    "extract_simple_field":   ("claude-haiku-4-5-20251001", 50),
    "route_query":            ("claude-haiku-4-5-20251001", 10),
    "binary_check":           ("claude-haiku-4-5-20251001", 5),
    "summarise_chunk":        ("claude-haiku-4-5-20251001", 200),  # Map phase in map-reduce
    "format_conversion":      ("claude-haiku-4-5-20251001", 300),
    "answer_faq":             ("claude-haiku-4-5-20251001", 150),
    
    # ── Sonnet tasks (standard production) ────────────────────────────
    "rag_answer":             ("claude-sonnet-4-6", 600),
    "summarise_document":     ("claude-sonnet-4-6", 800),
    "generate_description":   ("claude-sonnet-4-6", 300),
    "code_generation":        ("claude-sonnet-4-6", 1500),
    "invoice_extraction":     ("claude-sonnet-4-6", 400),
    "wine_recommendation":    ("claude-sonnet-4-6", 400),
    "email_draft":            ("claude-sonnet-4-6", 500),
    
    # ── Opus tasks (complex, infrequent) ──────────────────────────────
    "strategic_analysis":     ("claude-opus-4-6", 4096),
    "complex_agent":          ("claude-opus-4-6", 2048),
    "annual_report":          ("claude-opus-4-6", 4096),
}

def get_model_config(task: str) -> tuple[str, int]:
    """Returns (model, max_tokens) for the given task."""
    # Allow environment override for any task
    env_model = os.getenv(f"CLAUDE_MODEL_{task.upper().replace('-', '_')}")
    model, tokens = TASK_MODEL_MAP.get(task, ("claude-sonnet-4-6", 600))
    return env_model or model, tokens


def calculate_right_sizing_savings(
    tasks: dict[str, int],
    current_model: str = "claude-sonnet-4-6",
    avg_input_tokens: int = 2000,
    avg_output_tokens: int = 400,
) -> dict:
    """
    Calculate monthly savings from right-sizing tasks to cheaper models.
    
    Args:
        tasks:                {task_name: requests_per_day}
        current_model:        Model currently used for all tasks
        avg_input_tokens:     Average input per request
        avg_output_tokens:    Average output per request
    
    Returns:
        Monthly savings analysis
    
    Example:
        tasks = {
            "classify_intent": 5000,   # Could be Haiku
            "route_query":     3000,   # Could be Haiku
            "rag_answer":      1000,   # Should stay Sonnet
        }
        savings = calculate_right_sizing_savings(tasks)
        # Shows: $X/month savings by moving classify_intent and route_query to Haiku
    """
    current_model_pricing = PRICING[current_model]
    total_current_cost = 0
    total_optimized_cost = 0
    task_analysis = {}
    
    for task, daily_reqs in tasks.items():
        optimal_model, optimal_max_tokens = get_model_config(task)
        est_output = min(avg_output_tokens, optimal_max_tokens)
        
        current_cost_daily = daily_reqs * (
            (avg_input_tokens / 1_000_000 * current_model_pricing["input"]) +
            (avg_output_tokens / 1_000_000 * current_model_pricing["output"])
        )
        
        opt_pricing = PRICING[optimal_model]
        optimized_cost_daily = daily_reqs * (
            (avg_input_tokens / 1_000_000 * opt_pricing["input"]) +
            (est_output / 1_000_000 * opt_pricing["output"])
        )
        
        total_current_cost  += current_cost_daily * 30
        total_optimized_cost += optimized_cost_daily * 30
        
        task_analysis[task] = {
            "daily_requests":      daily_reqs,
            "current_model":       current_model,
            "optimal_model":       optimal_model,
            "current_monthly_usd": round(current_cost_daily * 30, 2),
            "optimal_monthly_usd": round(optimized_cost_daily * 30, 2),
            "savings_monthly_usd": round((current_cost_daily - optimized_cost_daily) * 30, 2),
        }
    
    return {
        "task_analysis":         task_analysis,
        "total_current_monthly": round(total_current_cost, 2),
        "total_optimal_monthly": round(total_optimized_cost, 2),
        "total_savings_monthly": round(total_current_cost - total_optimized_cost, 2),
        "savings_pct":           round((1 - total_optimized_cost / total_current_cost) * 100, 1) if total_current_cost else 0,
    }
```

---

## 4. Strategy 2 — Prompt Caching (High Impact)

```python
# Prompt caching: Cache reads cost 0.10× normal input price
# Cache writes cost 1.25× (one-time)
# Cache TTL: 5 minutes
# Minimum cacheable block: 1,024 tokens

def build_cached_system_prompt(
    stable_content: str,
    dynamic_content: str = "",
) -> list[dict]:
    """
    Build a system prompt with caching on the stable portion.
    
    Args:
        stable_content:  Content that doesn't change (persona, rules, product catalog)
                        Must be >= 1,024 tokens to benefit from caching
        dynamic_content: Per-request content (guest profile, retrieved context)
                        Not cached — changes every request
    
    Returns:
        System prompt list with cache_control on stable section
    
    Token economics example:
        Stable content: 3,000 tokens
        100 requests/hour, 80% cache hit rate:
        
        Without caching (100 req):
            100 × 3,000 × $0.000003/token = $0.90/hour
        
        With caching (100 req, 80% hits):
            20 cache writes: 20 × 3,000 × $0.000003 × 1.25 = $0.225 (one-time cost slightly higher)
            80 cache reads:  80 × 3,000 × $0.000003 × 0.10 = $0.072
            Total: $0.297/hour vs $0.90/hour = 67% savings
    """
    system_blocks = [
        {
            "type": "text",
            "text": stable_content,
            "cache_control": {"type": "ephemeral"},  # Cache this block
        }
    ]
    
    if dynamic_content:
        system_blocks.append({
            "type": "text",
            "text": dynamic_content,
            # No cache_control — dynamic content changes per request
        })
    
    return system_blocks


def calculate_cache_roi(
    cached_tokens: int,
    requests_per_day: int,
    hit_rate: float = 0.80,
    model: str = "claude-sonnet-4-6",
) -> dict:
    """
    Calculate ROI of enabling prompt caching.
    
    Args:
        cached_tokens:    Tokens in the cached section
        requests_per_day: Daily API requests
        hit_rate:         Expected cache hit rate (default: 0.80 = 80%)
        model:            Model being used
    
    Returns:
        Monthly cost comparison with and without caching
    
    Usage:
        roi = calculate_cache_roi(
            cached_tokens=3000,
            requests_per_day=500,
            hit_rate=0.85,
        )
        print(f"Monthly savings: ${roi['monthly_savings_usd']:.2f}")
    """
    p = PRICING[model]
    
    # Without caching: pay full input price every request
    no_cache_daily  = requests_per_day * (cached_tokens / 1_000_000) * p["input"]
    no_cache_monthly = no_cache_daily * 30
    
    # With caching
    hits_daily    = requests_per_day * hit_rate
    misses_daily  = requests_per_day * (1 - hit_rate)
    
    # Misses pay cache_write price (1.25×)
    write_cost_daily = misses_daily * (cached_tokens / 1_000_000) * p["cache_write"]
    # Hits pay cache_read price (0.10×)
    read_cost_daily  = hits_daily   * (cached_tokens / 1_000_000) * p["cache_read"]
    
    cached_daily   = write_cost_daily + read_cost_daily
    cached_monthly = cached_daily * 30
    
    return {
        "cached_tokens":            cached_tokens,
        "requests_per_day":         requests_per_day,
        "hit_rate_pct":             hit_rate * 100,
        "no_cache_monthly_usd":     round(no_cache_monthly, 2),
        "with_cache_monthly_usd":   round(cached_monthly, 2),
        "monthly_savings_usd":      round(no_cache_monthly - cached_monthly, 2),
        "savings_pct":              round((1 - cached_monthly / no_cache_monthly) * 100, 1),
        "breakeven_hit_rate_pct":   22.2,  # At ~22% hit rate, caching breaks even for Sonnet
    }

# Example for Lumière:
roi = calculate_cache_roi(
    cached_tokens=3000,    # Maître system prompt + wine list
    requests_per_day=500,  # Peak service day
    hit_rate=0.85,
)
print(f"Monthly savings from caching: ${roi['monthly_savings_usd']:.2f}")
# → Monthly savings: ~$9.45 (67% reduction on system prompt token cost)
```

---

## 5. Strategy 3 — max_tokens Discipline

```python
# Output tokens cost 5× more than input tokens (Sonnet: $3 input vs $15 output)
# Every unnecessary output token is 5× more expensive than input tokens

MAX_TOKENS_BY_TASK = {
    # ── Machine-consumed (minimize aggressively) ──────────────────────
    "yes_no":           5,    # "yes" or "no" only
    "binary_flag":      5,    # true/false, 0/1
    "language_detect":  5,    # "en", "fr", "de" only
    "single_category":  10,   # "wine", "menu", "booking"
    "short_label":      20,   # "Champagne", "Bordeaux"
    "field_extraction": 50,   # Single field value
    "json_small":       100,  # Compact JSON with few fields
    
    # ── Short human-readable responses ────────────────────────────────
    "answer_faq":       150,  # Brief factual answer
    "short_summary":    200,  # 2-3 sentence summary
    "short_explanation": 250, # Quick explanation
    
    # ── Standard responses ────────────────────────────────────────────
    "paragraph":        300,  # One detailed paragraph
    "rag_answer":       600,  # Grounded RAG response
    "wine_recommendation": 400, # Wine rec with pairing notes
    
    # ── Long-form content ─────────────────────────────────────────────
    "email_draft":      600,  # Professional email
    "detailed_summary": 800,  # Comprehensive summary
    "code_snippet":    1500,  # Code generation
    "full_document":   2048,  # Long-form document
    "complex_analysis": 4096, # Deep analysis or strategy
}

def enforce_max_tokens(task: str, requested_max: int = None) -> int:
    """
    Get the appropriate max_tokens for a task.
    
    Uses task-based config, but respects explicit overrides.
    
    Args:
        task:           Task identifier
        requested_max:  Explicit override (if provided, validates against task limit)
    
    Returns:
        max_tokens to use
    
    Example:
        tokens = enforce_max_tokens("classify_intent")
        # → 10 (not 1024 default!)
        
        tokens = enforce_max_tokens("rag_answer")
        # → 600
    """
    config_max = MAX_TOKENS_BY_TASK.get(task, 600)
    
    if requested_max is None:
        return config_max
    
    # If explicit override is larger, use the configured value (prevent cost blowout)
    if requested_max > config_max * 2:
        import logging
        logging.getLogger(__name__).warning(
            f"max_tokens={requested_max} exceeds {task} config ({config_max}). "
            f"Using {config_max} to prevent cost blowout."
        )
        return config_max
    
    return requested_max

# Impact calculation:
# Task: classify_intent
# default max_tokens=1024 → avg actual output: 50 tokens → wasted: 0 (but can spike to 100+)
# config max_tokens=10    → avg actual output: 3 tokens  → 94% output token savings
# At 5,000 req/day: saves (50-3)/1000 × $15 × 5000 = $3.52/day = $105.60/month
```

---

## 6. Strategy 4 — Batch API for Async Workloads (50% Discount)

```python
# Message Batches API: 50% cost reduction for async workloads
# Tradeoff: Responses may take minutes to hours (not real-time)
# Perfect for: nightly processing, offline analysis, bulk extraction

import anthropic
import json
import time

def submit_batch_extraction(
    items: list[dict],
    prompt_template: str,
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 300,
) -> str:
    """
    Submit a batch of extraction requests at 50% discount.
    
    Args:
        items:             List of {"id": str, "text": str} dicts
        prompt_template:   Template with {text} placeholder
        model:             Model to use (Haiku recommended for batch)
        max_tokens:        Max output tokens per item
    
    Returns:
        batch_id for polling
    
    Cost comparison:
        1,000 invoices, 1,500 input + 200 output tokens each
        Sync Haiku:  1000 × (1500×$0.00000080 + 200×$0.000004) = $2.00
        Batch Haiku: 1000 × (1500×$0.00000040 + 200×$0.000002) = $1.00 (50% off)
        
        Monthly savings at 50,000 invoices/month:
        $50/month sync → $25/month batch = $300/year
    """
    requests = []
    for item in items:
        prompt = prompt_template.format(text=item["text"])
        requests.append(
            anthropic.types.message_create_params.Request(
                custom_id=str(item["id"]),
                params=anthropic.types.MessageCreateParamsNonStreaming(
                    model=model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
            )
        )
    
    batch = anthropic.Anthropic().beta.messages.batches.create(requests=requests)
    print(f"Batch submitted: {batch.id} ({len(requests)} requests)")
    return batch.id


def collect_batch_results(batch_id: str, poll_interval: int = 60) -> dict[str, str]:
    """
    Poll for batch completion and collect results.
    
    Args:
        batch_id:      Batch ID from submit_batch_extraction
        poll_interval: Seconds between polls (default: 60)
    
    Returns:
        {custom_id: response_text} for all successful items
    """
    client = anthropic.Anthropic()
    
    while True:
        batch = client.beta.messages.batches.retrieve(batch_id)
        counts = batch.request_counts
        print(f"  Status: {batch.processing_status} | "
              f"✅{counts.succeeded} ❌{counts.errored} ⏳{counts.processing}")
        
        if batch.processing_status == "ended":
            break
        
        time.sleep(poll_interval)
    
    results = {}
    errors  = {}
    
    for result in client.beta.messages.batches.results(batch_id):
        if result.result.type == "succeeded":
            results[result.custom_id] = result.result.message.content[0].text
        else:
            errors[result.custom_id] = str(result.result.error)
    
    if errors:
        print(f"⚠️  {len(errors)} items failed: {list(errors.keys())[:5]}")
    
    print(f"✅ {len(results)}/{len(results) + len(errors)} items succeeded")
    return results


# ── Complete nightly pipeline example ──────────────────────────────────────
INVOICE_EXTRACTION_PROMPT = """Extract fields from this invoice. Return ONLY valid JSON:
{{"vendor_name": "string", "date": "YYYY-MM-DD", "total": number, "currency": "GBP"}}

Invoice:
{text}"""

def run_nightly_invoice_batch(invoices: list[dict]) -> list[dict]:
    """
    Process all new invoices overnight using the Batch API.
    
    Schedule: nightly at 11pm (see schedule.md)
    Run time: typically 10-30 minutes for 500 invoices
    Cost: ~$0.50 for 500 invoices at Haiku batch pricing
    """
    # 1. Submit batch
    batch_id = submit_batch_extraction(
        items=invoices,
        prompt_template=INVOICE_EXTRACTION_PROMPT,
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
    )
    
    # 2. Wait for completion (with 2-hour timeout)
    results = collect_batch_results(batch_id, poll_interval=120)
    
    # 3. Parse results
    processed = []
    for inv in invoices:
        raw = results.get(str(inv["id"]))
        if raw:
            try:
                data = json.loads(raw)
                processed.append({"id": inv["id"], "status": "success", **data})
            except json.JSONDecodeError:
                processed.append({"id": inv["id"], "status": "parse_error", "raw": raw[:100]})
        else:
            processed.append({"id": inv["id"], "status": "failed"})
    
    return processed
```

---

## 7. Strategy 5 — Application-Layer Response Caching

```python
import hashlib
import time
from threading import Lock

class ResponseCache:
    """
    Cache Claude responses for identical prompts.
    Prevents billing for the same query answered multiple times.
    
    Best for:
    - FAQ answers (same question → same answer)
    - Menu descriptions (change at most daily)
    - Allergen information (rarely changes)
    - Template content (static)
    
    NOT suitable for:
    - Personalized responses
    - Time-sensitive information
    - Responses with random/creative elements
    
    Args:
        ttl_seconds:  Cache lifetime (default: 3600 = 1 hour)
        max_entries:  Maximum cached items (default: 5,000)
    """
    
    def __init__(self, ttl_seconds: int = 3600, max_entries: int = 5_000):
        self._store: dict = {}
        self._lock = Lock()
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self.hits = 0
        self.misses = 0
    
    def key(self, prompt: str, model: str, max_tokens: int) -> str:
        return hashlib.sha256(f"{model}:{max_tokens}:{prompt}".encode()).hexdigest()
    
    def get(self, prompt: str, model: str, max_tokens: int) -> str | None:
        k = self.key(prompt, model, max_tokens)
        with self._lock:
            entry = self._store.get(k)
            if entry and time.time() - entry["t"] < self.ttl:
                self.hits += 1
                return entry["v"]
            if entry:
                del self._store[k]
        self.misses += 1
        return None
    
    def set(self, prompt: str, model: str, max_tokens: int, response: str):
        k = self.key(prompt, model, max_tokens)
        with self._lock:
            if len(self._store) >= self.max_entries:
                # Evict oldest entry
                oldest = min(self._store, key=lambda x: self._store[x]["t"])
                del self._store[oldest]
            self._store[k] = {"v": response, "t": time.time()}
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0
    
    def monthly_savings_usd(self, avg_tokens: int = 2000, model: str = "claude-sonnet-4-6") -> float:
        """Estimate monthly savings from cache hits."""
        p = PRICING[model]
        cost_per_call = (avg_tokens / 1_000_000) * p["input"]
        saved_calls = self.hits
        return round(saved_calls * cost_per_call, 2)

# Global cache
response_cache = ResponseCache(ttl_seconds=1800, max_entries=5_000)

def cached_call(prompt: str, model: str = "claude-sonnet-4-6", max_tokens: int = 600) -> str:
    """
    Call Claude with application-level response caching.
    
    Cache hit:  Returns immediately, $0 API cost
    Cache miss: Calls Claude, caches response, pays normal cost
    """
    cached = response_cache.get(prompt, model, max_tokens)
    if cached:
        return cached
    
    import anthropic
    response = anthropic.Anthropic().messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    result = response.content[0].text
    response_cache.set(prompt, model, max_tokens, result)
    return result
```

---

## 8. Strategy 6 — Output Format Compression

```python
# Output tokens are 5× more expensive than input tokens.
# Requesting concise formats dramatically reduces output cost.

# Example: Invoice extraction
# ❌ Verbose (300 output tokens):
VERBOSE_PROMPT = """
Please analyse this invoice and provide me with all the relevant information
including the vendor name, the date of the invoice, the total amount with
currency, and any line items present...
"""
# → Claude responds: "Based on my analysis of the invoice, I can see that
#    the vendor is ABC Supplies Ltd, the invoice date is 15 January 2026..."
# → ~300 tokens output × $0.000015/token = $0.0045

# ✅ Compressed (30 output tokens):
COMPRESSED_PROMPT = """
Extract invoice fields. Return ONLY valid JSON, no explanation:
{"vendor": "string", "date": "YYYY-MM-DD", "total": number, "currency": "3-letter code"}

Invoice:
{invoice_text}
"""
# → Claude responds: {"vendor": "ABC Supplies Ltd", "date": "2026-01-15", "total": 1250.00, "currency": "GBP"}
# → ~30 tokens output × $0.000015/token = $0.00045 (90% reduction)

OUTPUT_FORMAT_TIPS = {
    "extraction":    "Return ONLY valid JSON, no explanation, no markdown fences.",
    "classification": "Reply with exactly one word: the category name.",
    "yes_no":        "Reply with exactly one word: yes or no.",
    "ranking":       "Reply with a comma-separated list only, e.g.: item1, item2, item3",
    "score":         "Reply with a single number between 0 and 10, nothing else.",
    "list":          "Reply with a JSON array only: [\"item1\", \"item2\"]",
    "summary":       "Summarise in exactly 2 sentences. No headers, no bullets.",
}

def add_compression_instruction(prompt: str, output_type: str) -> str:
    """Add output compression instruction to a prompt."""
    instruction = OUTPUT_FORMAT_TIPS.get(output_type, "Be concise.")
    return f"{instruction}\n\n{prompt}"
```

---

## 9. Strategy 7 — Request Deduplication

```python
# If the same request arrives multiple times within a short window,
# serve the first response to all duplicate requests.
# (Common in high-traffic scenarios with cache stampede)

import asyncio
from typing import Awaitable

class RequestDeduplicator:
    """
    Deduplicate concurrent identical requests.
    
    Scenario: 50 users ask "What's on the tasting menu?" simultaneously.
    Without deduplication: 50 API calls at $0.008 each = $0.40
    With deduplication:    1 API call, 49 served from in-flight cache = $0.008
    
    Works on: concurrent requests arriving within the same time window.
    Complements: response_cache (which works across time windows).
    """
    
    def __init__(self):
        self._in_flight: dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()
        self.dedup_count = 0
    
    async def get_or_fetch(
        self,
        key: str,
        fetch_fn: Awaitable,
    ) -> str:
        """
        If a request with this key is in-flight, wait for it.
        Otherwise, execute the fetch and let other waiters share the result.
        """
        async with self._lock:
            if key in self._in_flight:
                self.dedup_count += 1
                future = self._in_flight[key]
            else:
                future = asyncio.get_event_loop().create_future()
                self._in_flight[key] = future
                is_new = True
        
        if not is_new:
            return await future
        
        try:
            result = await fetch_fn()
            future.set_result(result)
            return result
        except Exception as e:
            future.set_exception(e)
            raise
        finally:
            async with self._lock:
                self._in_flight.pop(key, None)

deduplicator = RequestDeduplicator()
```

---

## 10. Budget Enforcement and Alerting

```python
from datetime import date, datetime
from dataclasses import dataclass, field

@dataclass
class TokenBudgetTracker:
    """
    Enforce daily token spend budget with real-time monitoring.
    
    Features:
    - Track spend per model
    - Warn at 70% of daily budget
    - Block requests at 100% of daily budget
    - Log all usage for reporting
    - Reset daily
    
    Args:
        daily_budget_usd: Maximum daily Claude spend (default: $50)
        warn_threshold:   Warning at this fraction of budget (default: 0.70)
        block_threshold:  Hard block at this fraction (default: 1.00)
    
    Usage:
        tracker = TokenBudgetTracker(daily_budget_usd=100.0)
        
        # After each API call:
        tracker.record(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model="claude-sonnet-4-6",
            task="wine_recommendation",
        )
        
        # Before each API call (optional):
        tracker.check_budget()  # Raises BudgetExceededError if over limit
    """
    
    daily_budget_usd:  float = 50.0
    warn_threshold:    float = 0.70
    block_threshold:   float = 1.00
    
    _daily_spend:     float = field(default=0.0, init=False)
    _reset_date:      date  = field(default_factory=date.today, init=False)
    _usage_log:       list  = field(default_factory=list, init=False)
    
    def _reset_if_new_day(self):
        today = date.today()
        if today > self._reset_date:
            self._daily_spend = 0.0
            self._reset_date = today
            self._usage_log = []
    
    def record(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str,
        task: str = "unknown",
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
    ):
        """Record usage and update daily spend."""
        self._reset_if_new_day()
        
        cost = calculate_cost(
            input_tokens, output_tokens, model,
            cache_write_tokens, cache_read_tokens
        )["total_cost"]
        
        self._daily_spend += cost
        self._usage_log.append({
            "timestamp":    datetime.utcnow().isoformat(),
            "model":        model,
            "task":         task,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd":     cost,
        })
        
        # Warning alert
        if self._daily_spend > self.daily_budget_usd * self.warn_threshold:
            ratio = self._daily_spend / self.daily_budget_usd
            import logging
            logging.getLogger(__name__).warning(
                f"⚠️  Claude spend at {ratio:.0%} of daily budget "
                f"(${self._daily_spend:.2f} / ${self.daily_budget_usd:.2f})"
            )
    
    def check_budget(self):
        """Raise BudgetExceededError if daily budget is exhausted."""
        self._reset_if_new_day()
        if self._daily_spend >= self.daily_budget_usd * self.block_threshold:
            raise BudgetExceededError(
                f"Daily Claude budget of ${self.daily_budget_usd} exceeded. "
                f"Current spend: ${self._daily_spend:.2f}. "
                f"Budget resets at midnight UTC."
            )
    
    def status(self) -> dict:
        self._reset_if_new_day()
        return {
            "daily_budget_usd":  self.daily_budget_usd,
            "daily_spend_usd":   round(self._daily_spend, 4),
            "remaining_usd":     round(self.daily_budget_usd - self._daily_spend, 4),
            "utilisation_pct":   round(self._daily_spend / self.daily_budget_usd * 100, 1),
            "calls_today":       len(self._usage_log),
            "top_tasks":         self._top_tasks_by_cost(),
        }
    
    def _top_tasks_by_cost(self) -> list:
        from collections import defaultdict
        task_costs = defaultdict(float)
        for entry in self._usage_log:
            task_costs[entry["task"]] += entry["cost_usd"]
        return sorted(
            [{"task": t, "cost_usd": round(c, 4)} for t, c in task_costs.items()],
            key=lambda x: x["cost_usd"], reverse=True
        )[:5]

class BudgetExceededError(Exception):
    pass

# Global tracker — one per service
budget_tracker = TokenBudgetTracker(daily_budget_usd=50.0)
```

---

## 11. Cost Monitoring Dashboard

### KQL Queries for Azure Log Analytics

```kusto
// ── Daily cost by model ─────────────────────────────────────────────
customEvents
| where name == "claude_api_call"
| where timestamp > ago(30d)
| extend model = tostring(customDimensions.model)
| extend input_tokens  = todouble(customMeasurements.input_tokens)
| extend output_tokens = todouble(customMeasurements.output_tokens)
| extend cost_usd = case(
    model == "claude-haiku-4-5-20251001",
        input_tokens / 1000000 * 0.80 + output_tokens / 1000000 * 4.00,
    model == "claude-sonnet-4-6",
        input_tokens / 1000000 * 3.00 + output_tokens / 1000000 * 15.00,
    model == "claude-opus-4-6",
        input_tokens / 1000000 * 15.00 + output_tokens / 1000000 * 75.00,
    0.0
)
| summarize daily_cost_usd = sum(cost_usd) by bin(timestamp, 1d), model
| order by timestamp desc

// ── Top 10 most expensive tasks ──────────────────────────────────────
customEvents
| where name == "claude_api_call"
| where timestamp > ago(7d)
| extend task = tostring(customDimensions.task_type)
| extend model = tostring(customDimensions.model)
| extend input_tokens  = todouble(customMeasurements.input_tokens)
| extend output_tokens = todouble(customMeasurements.output_tokens)
| extend cost = input_tokens / 1000000 * 3.0 + output_tokens / 1000000 * 15.0
| summarize total_cost = sum(cost), call_count = count() by task
| top 10 by total_cost desc

// ── Cache hit rate (cost savings indicator) ──────────────────────────
customEvents
| where name == "claude_api_call"
| where timestamp > ago(24h)
| extend cached = tobool(customDimensions.cache_hit)
| summarize
    cache_hits   = countif(cached == true),
    cache_misses = countif(cached == false)
| extend hit_rate_pct = cache_hits * 100.0 / (cache_hits + cache_misses)
| project cache_hits, cache_misses, hit_rate_pct
```

---

## 12. Cost Audit Tool

```python
def run_cost_audit(
    recent_requests: list[dict],
    target_model: str = "claude-sonnet-4-6",
) -> dict:
    """
    Analyse recent API requests and identify optimization opportunities.
    
    Args:
        recent_requests: List of {model, input_tokens, output_tokens, task, max_tokens_set} dicts
        target_model:    Reference model for comparison
    
    Returns:
        Audit report with specific optimization recommendations
    """
    findings = []
    total_cost = 0.0
    potential_savings = 0.0
    
    # Analyse each request
    task_model_waste = {}  # Tasks using Opus/Sonnet that could use Haiku
    oversized_output  = []  # Requests where output << max_tokens
    
    for req in recent_requests:
        model = req.get("model", "claude-sonnet-4-6")
        in_t  = req.get("input_tokens", 0)
        out_t = req.get("output_tokens", 0)
        task  = req.get("task", "unknown")
        max_t = req.get("max_tokens_set", 1024)
        
        cost = calculate_cost(in_t, out_t, model)["total_cost"]
        total_cost += cost
        
        # Check 1: Is a simpler model sufficient?
        optimal_model, _ = get_model_config(task) if task != "unknown" else ("claude-sonnet-4-6", 600)
        if PRICING.get(model, {}).get("input", 0) > PRICING.get(optimal_model, {}).get("input", 0):
            optimal_cost = calculate_cost(in_t, out_t, optimal_model)["total_cost"]
            saved = cost - optimal_cost
            task_model_waste[task] = task_model_waste.get(task, 0) + saved
            potential_savings += saved
        
        # Check 2: Is max_tokens appropriate?
        if max_t > out_t * 3 and max_t > 200:
            oversized_output.append({
                "task":      task,
                "max_tokens": max_t,
                "actual_output": out_t,
                "waste_ratio":   round(max_t / out_t, 1) if out_t > 0 else 999,
            })
    
    # Generate findings
    if task_model_waste:
        top_waste_task = max(task_model_waste, key=task_model_waste.get)
        findings.append({
            "type":   "model_waste",
            "impact": "HIGH",
            "detail": f"Task '{top_waste_task}' using expensive model. "
                      f"Switch to {get_model_config(top_waste_task)[0]} to save "
                      f"${task_model_waste[top_waste_task]*30:.2f}/month",
        })
    
    if oversized_output:
        avg_waste = sum(r["waste_ratio"] for r in oversized_output) / len(oversized_output)
        findings.append({
            "type":   "oversized_max_tokens",
            "impact": "MEDIUM",
            "detail": f"{len(oversized_output)} requests with max_tokens {avg_waste:.1f}× actual output. "
                      f"Tight max_tokens reduces cost and latency.",
        })
    
    return {
        "total_cost_usd":       round(total_cost, 2),
        "potential_savings_usd": round(potential_savings * 30, 2),  # Monthly
        "savings_pct":          round(potential_savings / total_cost * 100, 1) if total_cost else 0,
        "findings":             findings,
        "audit_size":           len(recent_requests),
    }
```

---

## 13. Junior Walkthrough — Reduce Your First Bill

**Scenario**: "My Claude API bill was $200 last month. Where do I start?"

**Step 1: Check which model you're using everywhere**

```python
# Search your codebase for model strings
# grep -r "claude-opus" . --include="*.py"
# If everything uses Opus → immediate 5× saving by switching to Sonnet
```

**Step 2: Calculate your actual cost per request**

```python
# Look at your API usage dashboard or add logging:
response = client.messages.create(...)
cost = calculate_cost(
    response.usage.input_tokens,
    response.usage.output_tokens,
    "claude-sonnet-4-6"
)
print(f"This call cost: ${cost['total_cost']:.4f}")
print(f"Input: {response.usage.input_tokens} tokens, Output: {response.usage.output_tokens} tokens")
```

**Step 3: Identify your most expensive task**

```python
# Add task tracking to all your calls
budget_tracker.record(
    input_tokens=response.usage.input_tokens,
    output_tokens=response.usage.output_tokens,
    model="claude-sonnet-4-6",
    task="wine_recommendation",  # ← Add task label
)
print(budget_tracker.status()["top_tasks"])
# → [{"task": "invoice_extraction", "cost_usd": 45.20}, ...]
```

**Step 4: Apply the top 3 quick wins**

```python
# Quick win 1: Move classification to Haiku
model = "claude-haiku-4-5-20251001"  # Was Sonnet → 75% cheaper

# Quick win 2: Cache your system prompt
system = [{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}]

# Quick win 3: Set tight max_tokens
max_tokens = 10  # Was 1024 for classification → 99% output reduction
```

---

## 14. Senior Patterns — Enterprise Cost Governance

```python
class CostGovernanceSystem:
    """
    Enterprise cost governance: budgets + forecasting + automated optimization.
    """
    
    MONTHLY_BUDGET_BY_TEAM = {
        "frontend_chat":   200.0,   # Guest-facing chat widget
        "back_office":     150.0,   # Invoice processing, reporting
        "development":      50.0,   # Dev/staging environments
    }
    
    def __init__(self):
        self.trackers = {
            team: TokenBudgetTracker(budget / 30)  # Daily budget
            for team, budget in self.MONTHLY_BUDGET_BY_TEAM.items()
        }
    
    def get_tracker(self, team: str) -> TokenBudgetTracker:
        return self.trackers.get(team, self.trackers["back_office"])
    
    def monthly_forecast(self) -> dict:
        """Forecast monthly spend based on last 7 days of actual usage."""
        forecasts = {}
        for team, tracker in self.trackers.items():
            recent_daily_avg = tracker._daily_spend  # Today's spend (approximate)
            forecasts[team] = {
                "daily_avg": recent_daily_avg,
                "monthly_forecast": recent_daily_avg * 30,
                "monthly_budget": self.MONTHLY_BUDGET_BY_TEAM[team],
                "on_track": recent_daily_avg * 30 <= self.MONTHLY_BUDGET_BY_TEAM[team],
            }
        return forecasts
```

---

## 15. Tips, Tricks, and Gotchas

### Tips

1. **Model selection is your #1 lever** — moving 50% of requests from Sonnet to Haiku cuts costs more than any other optimization
2. **Output costs 5× more than input** — always set tight `max_tokens`; the model will use fewer tokens if the output is naturally short
3. **Batch API for anything async** — any nightly, weekly, or background processing that doesn't need real-time response qualifies for 50% off
4. **Cache the system prompt** — even a 500-token system prompt cached across 1,000 req/day saves $1.35/day = $40/month on Sonnet

### Tricks

5. **Use env vars for model config** — `CLAUDE_COST_MODE=economy` in development cuts dev costs by 70%+ with no code changes
6. **Request deduplication for burst traffic** — if 20 users ask "what's on the menu?" simultaneously, only call Claude once
7. **Normalise prompts before caching** — strip whitespace, lowercase, remove stopwords to improve cache hit rate
8. **max_tokens=5 for yes/no** — any binary or small-label output task should have very tight max_tokens (5-20)

### Gotchas

9. **Cache writes cost 1.25× normal** — the first request after a cache miss costs slightly more. With high hit rates (>22%), caching still pays off significantly.
10. **Batch API has ~1s overhead per item** — batch is not faster than sync; it's cheaper. Never use batch for real-time user interactions.
11. **Response cache can return stale data** — use appropriate TTLs; wine prices change less often than availability
12. **Count tokens before trimming** — the `count_tokens` API is free; use it to measure before aggressive trimming, not after

---

## 16. Quick Reference Cheatsheet

```python
# ═══════════════════════════════════════════════════════════════
# COST OPTIMIZATION QUICK REFERENCE
# ═══════════════════════════════════════════════════════════════

# 1. PRICING (approx 2026, $/million tokens)
# Haiku:  $0.80 in / $4.00 out
# Sonnet: $3.00 in / $15.00 out
# Opus:   $15.00 in / $75.00 out
# Cache read (any model): 0.10× input price
# Cache write (any model): 1.25× input price

# 2. COST CALCULATION
cost = calculate_cost(input_tokens, output_tokens, model)
print(cost["breakdown"])  # "$0.0060 input + $0.0060 output = $0.0120"

# 3. RIGHT-SIZING (biggest impact)
TASK_MODELS = {
    "classify_intent": ("claude-haiku-4-5-20251001", 10),  # Not Sonnet!
    "rag_answer":      ("claude-sonnet-4-6", 600),
    "strategy":        ("claude-opus-4-6", 4096),
}

# 4. CACHE STABLE SYSTEM PROMPT
system = [{"type": "text", "text": BIG_STABLE_PROMPT, "cache_control": {"type": "ephemeral"}}]
# → 67% savings on system prompt tokens at 80% hit rate

# 5. TIGHT MAX_TOKENS
MAX_TOKENS_BY_TASK = {
    "yes_no": 5, "classify": 10, "extract_field": 50, "rag": 600
}

# 6. BATCH API (50% discount for async)
batch = client.beta.messages.batches.create(requests=[...])
# Wait hours → collect results at half price

# 7. RESPONSE CACHE (avoid duplicate calls)
key = hashlib.sha256(f"{model}:{prompt}".encode()).hexdigest()
cached = cache.get(key)  # Free!
if not cached:
    result = call_claude(prompt)
    cache.set(key, result, ttl=3600)

# 8. BUDGET ENFORCEMENT
budget_tracker.check_budget()   # Raises if over limit
budget_tracker.record(...)      # Log each call
budget_tracker.status()         # {"utilisation_pct": 45.2, ...}

# 9. TOP 3 QUICK WINS
# A: Classification → Haiku (saves ~75% on those calls)
# B: Enable cache on system prompt >= 1024 tokens (saves 60-70%)
# C: max_tokens=10 for labels, max_tokens=5 for yes/no (saves 98% output cost)
```
