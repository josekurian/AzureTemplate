# caching.md — Prompt Caching Deep Dive

> **Purpose**: Complete guide to Claude's prompt caching feature — from basics to production-grade caching architectures with ROI calculations, warming strategies, and multi-turn caching.  
> **Owner**: jose@hybridgenai.com  
> **Updated**: 2026-05-22

---

## Navigation

1. [How Prompt Caching Works](#1-how-prompt-caching-works)
2. [Marking Content for Caching](#2-marking-content-for-caching)
3. [Cache Placement Rules](#3-cache-placement-rules)
4. [What to Cache vs Not Cache](#4-what-to-cache-vs-not-cache)
5. [Cache TTL and Warming Strategy](#5-cache-ttl-and-warming-strategy)
6. [Multi-Turn Conversation Caching](#6-multi-turn-conversation-caching)
7. [Tool Definition Caching](#7-tool-definition-caching)
8. [ROI Calculation](#8-roi-calculation)
9. [Monitoring Cache Performance](#9-monitoring-cache-performance)
10. [Junior Quick-Start Walkthrough](#10-junior-quick-start-walkthrough)
11. [Senior Patterns and Production Hardening](#11-senior-patterns-and-production-hardening)
12. [Tips, Tricks and Gotchas](#12-tips-tricks-and-gotchas)
13. [Quick Reference Cheatsheet](#13-quick-reference-cheatsheet)

---

## 1. How Prompt Caching Works

Claude's prompt caching stores the KV (key-value attention) cache of your processed prompt on Anthropic's servers. On the next request that reuses the same prefix, Claude skips recomputing those tokens.

```
WITHOUT CACHING:
  Request 1: [System: 8,000 tokens] + [User: 100 tokens] → Process 8,100 tokens
  Request 2: [System: 8,000 tokens] + [User: 120 tokens] → Process 8,120 tokens
  Request 3: [System: 8,000 tokens] + [User: 90 tokens]  → Process 8,090 tokens
  Cost: 3 × ~8,100 × $3/MTok = $0.073

WITH CACHING (system prompt cached):
  Request 1: [System: 8,000 WRITE] + [User: 100 tokens] → Process 8,100 tokens (WRITE)
  Request 2: [System: 8,000 HIT]   + [User: 120 tokens] → Process only 120 tokens
  Request 3: [System: 8,000 HIT]   + [User: 90 tokens]  → Process only 90 tokens
  Cost: (8,100 × $3.75) + (120 × $0.30) + (90 × $0.30) = $0.030 + $0.000036 + $0.000027
       = $0.030 (59% savings on just 3 requests — improves dramatically at scale)
```

**Pricing model:**

```python
# Caching pricing as of 2026-05-22 (per million tokens):
CACHE_PRICING = {
    "claude-sonnet-4-6": {
        "normal_input": 3.00,         # $3.00/MTok — standard rate
        "cache_write": 3.75,          # 1.25× normal — one-time write cost
        "cache_read": 0.30,           # 0.10× normal — 90% discount on hits
    },
    "claude-haiku-4-5-20251001": {
        "normal_input": 0.80,
        "cache_write": 1.00,          # 1.25× of $0.80
        "cache_read": 0.08,           # 0.10× of $0.80
    },
    "claude-opus-4-6": {
        "normal_input": 15.00,
        "cache_write": 18.75,
        "cache_read": 1.50,
    }
}
```

**Key constraint: Minimum 1,024 tokens** to be eligible for caching. Content shorter than 1,024 tokens cannot be cached.

---

## 2. Marking Content for Caching

Add `"cache_control": {"type": "ephemeral"}` to any content block you want cached.

### Caching a System Prompt

```python
import anthropic

client = anthropic.Anthropic()

# Small static prompt — probably not worth caching (<1,024 tokens)
SIMPLE_SYSTEM = "You are a helpful assistant."  # ~10 tokens

# Large static prompt — definitely cache this (>1,024 tokens)
RESTAURANT_SYSTEM = """
You are Maître, the AI concierge for Lumière restaurant in Mayfair, London.
[... 2,000 tokens of persona, scope, constraints, examples ...]
"""

# Caching via system as array of content blocks
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": RESTAURANT_SYSTEM,           # 2,000+ tokens
            "cache_control": {"type": "ephemeral"}  # ← Cache this
        }
        # Multiple blocks supported — each can have cache_control
    ],
    messages=[
        {"role": "user", "content": "What wines pair well with the halibut?"}
    ]
)

# Inspect cache usage
usage = response.usage
print(f"Input tokens (uncached):   {usage.input_tokens}")
print(f"Cache write tokens:        {getattr(usage, 'cache_creation_input_tokens', 0)}")
print(f"Cache read tokens (saved): {getattr(usage, 'cache_read_input_tokens', 0)}")
```

### Caching a Large Knowledge Document

```python
# Pattern: System prompt + large document, both cached
WINE_LIST_DOCUMENT = open("wine_list_2026.txt").read()  # ~6,000 tokens

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=[
        # Block 1: Persona and rules (stable — cache it)
        {
            "type": "text",
            "text": RESTAURANT_SYSTEM,
            "cache_control": {"type": "ephemeral"}
        },
        # Block 2: Wine list document (stable — cache it too)
        {
            "type": "text",
            "text": f"WINE LIST:\n{WINE_LIST_DOCUMENT}",
            "cache_control": {"type": "ephemeral"}
        }
        # NOTE: Up to 4 cache breakpoints per request
    ],
    messages=[
        # Dynamic content — NOT cached
        {"role": "user", "content": "I'd like a Burgundy under £80 for the fish course."}
    ]
)
```

### Caching in User Messages (for Long Documents)

```python
# When the user submits a large document for analysis, cache the document
LARGE_DOCUMENT = load_document("annual_report.pdf")  # 10,000 tokens

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2048,
    messages=[
        {
            "role": "user",
            "content": [
                # Cache the document (large, stable)
                {
                    "type": "text",
                    "text": f"Document to analyse:\n{LARGE_DOCUMENT}",
                    "cache_control": {"type": "ephemeral"}
                },
                # Dynamic: the question (not cached)
                {
                    "type": "text",
                    "text": "What were the three main revenue drivers this year?"
                }
            ]
        }
    ]
)
# Now the user can ask multiple follow-up questions about the same document
# without re-processing the 10,000-token document each time
```

---

## 3. Cache Placement Rules

**The cache covers the longest matching prefix.** Everything before the first dynamic content can be cached. Anything after dynamic content will NOT be cached.

```
✅ CORRECT — Static first, dynamic last:

   [BLOCK A: System prompt, cache_control] ← CACHED
   [BLOCK B: Wine list document, cache_control] ← CACHED
   [Dynamic: Today's specials] ← NOT cached (changes daily)
   [Dynamic: User question] ← NOT cached

   Cache covers: Block A + Block B (everything before first dynamic content)

❌ WRONG — Dynamic in the middle breaks the cache:

   [BLOCK A: System prompt, cache_control] ← CACHED
   [Dynamic: Today's date / specials] ← BREAKS CACHE PREFIX HERE
   [BLOCK B: Wine list, cache_control] ← This cache_control is INEFFECTIVE
   [Dynamic: User question]

   Cache covers: Block A only (prefix ends at first dynamic content)
```

**Practical rule**: Put your static cacheable content at the BEGINNING of your system prompt or message. Inject dynamic content (dates, user name, live data) only at the END.

```python
# Build system prompt in the right order:
def build_system_prompt(
    daily_specials: list[str] = None,
    user_name: str = None
) -> list[dict]:
    """
    Returns a list of content blocks in cache-optimal order:
    1. Static persona (cached)
    2. Static knowledge base (cached)
    3. Dynamic context (NOT cached — must come last)
    """
    blocks = [
        # Block 1: Static persona and rules — ALWAYS first
        {
            "type": "text",
            "text": RESTAURANT_PERSONA_AND_RULES,   # ~1,500 tokens, never changes
            "cache_control": {"type": "ephemeral"}
        },
        # Block 2: Static wine list — SECOND (also cached)
        {
            "type": "text",
            "text": WINE_LIST,                      # ~5,000 tokens, changes monthly
            "cache_control": {"type": "ephemeral"}
        },
    ]

    # Block 3: Dynamic content — LAST (not cached)
    dynamic_parts = []
    if daily_specials:
        dynamic_parts.append(f"TODAY'S SPECIALS: {', '.join(daily_specials)}")
    if user_name:
        dynamic_parts.append(f"Speaking with: {user_name}")
    if dynamic_parts:
        blocks.append({"type": "text", "text": "\n".join(dynamic_parts)})
        # Note: No cache_control here — dynamic content not cached

    return blocks
```

---

## 4. What to Cache vs Not Cache

```python
# ✅ GOOD cache candidates — large, stable, reused across requests
CACHE_THESE = {
    "persona_rules": "System prompt persona, scope, constraints, output format (500-3,000 tokens)",
    "few_shot_examples": "3-5 example Q&A pairs appended to system prompt (500-2,000 tokens)",
    "static_documents": "Menus, wine lists, policies, handbooks (1,000-50,000 tokens)",
    "tool_definitions": "All tool schemas (rarely change between requests)",
    "code_context": "Large codebase files in coding assistants",
    "reference_data": "Price lists, product catalogs, regulatory documents",
    "training_material": "Standard operating procedures, FAQs",
}

# ❌ POOR cache candidates — dynamic, short, or unique per request
DO_NOT_CACHE = {
    "user_messages": "Always unique — never cache (no benefit)",
    "rag_chunks": "Change per query — don't cache (cache miss every time)",
    "timestamps": "Change every second — breaks cache prefix",
    "session_ids": "Unique per session — same issue",
    "real_time_data": "Stock prices, availability — changes constantly",
    "personalisation": "User-specific content that varies — inject at end, no cache_control",
    "short_content": "Content <1,024 tokens — below minimum for caching",
}
```

---

## 5. Cache TTL and Warming Strategy

**Cache TTL**: Approximately 5 minutes of inactivity. The cache expires if no request uses it for 5+ minutes.

```
Cache lifecycle:
  Request 1 → Cache WRITE (pays 1.25×, ~50% slower than normal)
  Request 2 (within 5min) → Cache HIT (pays 0.10×, ~50% faster than normal)
  Request 3 (within 5min) → Cache HIT
  ...
  5+ minutes of inactivity → Cache EXPIRES
  Next request → Cache WRITE again
```

### Cache Warming Service

For production apps with sporadic traffic, keep the cache warm with periodic dummy requests.

```python
import asyncio
import time
from typing import Optional

class CacheWarmingService:
    """
    Keep prompt cache warm by sending periodic heartbeat requests.
    Prevents cache expiry during low-traffic periods.

    Usage:
        warmer = CacheWarmingService(stable_content=SYSTEM_PROMPT, model="claude-sonnet-4-6")
        await warmer.start()  # Run in background
    """

    CACHE_TTL_SECONDS = 300      # 5-minute cache TTL
    WARM_INTERVAL_SECONDS = 240  # Refresh every 4 minutes (before TTL)
    WARMING_MODEL = "claude-haiku-4-5-20251001"  # Cheapest model for warming

    def __init__(self, stable_content: str, model: str = "claude-sonnet-4-6"):
        self.stable_content = stable_content
        self.model = model
        self.last_warm_time: float = 0
        self.warm_count: int = 0
        self._running = False

    async def start(self):
        """Start the warming loop (run as background asyncio task)."""
        self._running = True
        while self._running:
            if self._should_warm():
                await self._send_warming_request()
            await asyncio.sleep(30)  # Check every 30 seconds

    def stop(self):
        self._running = False

    def _should_warm(self) -> bool:
        return time.time() - self.last_warm_time >= self.WARM_INTERVAL_SECONDS

    async def _send_warming_request(self):
        """Send minimal request to refresh the cache."""
        try:
            # Use a minimal prompt — just enough to trigger cache write
            response = client.messages.create(
                model=self.WARMING_MODEL,    # Use Haiku to minimise warming cost
                max_tokens=1,               # Minimal output — we don't need the response
                system=[{
                    "type": "text",
                    "text": self.stable_content,
                    "cache_control": {"type": "ephemeral"}
                }],
                messages=[{"role": "user", "content": "ping"}]
            )

            self.last_warm_time = time.time()
            self.warm_count += 1

            # Log cache write vs read
            write_tokens = getattr(response.usage, "cache_creation_input_tokens", 0)
            read_tokens = getattr(response.usage, "cache_read_input_tokens", 0)

            if write_tokens > 0:
                print(f"[CacheWarmer] Cache REFRESHED ({write_tokens} tokens written)")
            elif read_tokens > 0:
                print(f"[CacheWarmer] Cache still warm ({read_tokens} tokens hit)")

        except Exception as e:
            print(f"[CacheWarmer] Warning: warming request failed: {e}")
            # Don't re-raise — warming failures are non-fatal

# Startup:
async def main():
    warmer = CacheWarmingService(stable_content=RESTAURANT_FULL_SYSTEM_PROMPT)
    warming_task = asyncio.create_task(warmer.start())

    # ... rest of application ...

    # Shutdown:
    warmer.stop()
    await warming_task
```

### When NOT to Warm

```python
# Calculate warming cost vs benefit:
def should_warm_cache(
    requests_per_hour: float,
    stable_tokens: int,
    model: str = "claude-sonnet-4-6"
) -> dict:
    """
    Decide if cache warming is worth the cost.

    Warming is NOT worth it if requests are frequent enough to keep cache warm naturally.
    Warming IS worth it if there are extended idle periods between requests.
    """
    p = PRICING[model]

    # If >1 request per 4 minutes, cache stays warm naturally — no warming needed
    natural_requests_per_5min = requests_per_hour / 12

    if natural_requests_per_5min >= 1:
        return {
            "should_warm": False,
            "reason": "Traffic is frequent enough to keep cache warm naturally (>1 req/5min)"
        }

    # Calculate warming cost (1 warming request per 4 minutes = 15/hour = 360/day)
    warming_requests_per_day = 360
    warming_cost_per_day = warming_requests_per_day * stable_tokens / 1_000_000 * p["cache_write"]

    # Calculate savings from warming
    actual_requests_per_day = requests_per_hour * 24
    savings_from_caching = (actual_requests_per_day *
        stable_tokens / 1_000_000 * (p["normal_input"] - p["cache_read"]))

    net_benefit = savings_from_caching - warming_cost_per_day

    return {
        "should_warm": net_benefit > 0,
        "warming_cost_per_day_usd": round(warming_cost_per_day, 4),
        "savings_from_caching_per_day_usd": round(savings_from_caching, 4),
        "net_benefit_per_day_usd": round(net_benefit, 4),
        "reason": "Warming saves more than it costs" if net_benefit > 0 else "Not worth warming"
    }
```

---

## 6. Multi-Turn Conversation Caching

In multi-turn conversations, both the system prompt AND the growing conversation history can be cached.

```python
def build_multi_turn_cached_request(
    system_prompt: str,
    conversation_history: list[dict],
    new_user_message: str,
    cache_history_turns: int = 10
) -> dict:
    """
    Build a request that caches both the system prompt and stable conversation history.

    Strategy:
    - System prompt: always cached (stable)
    - First N turns of conversation: cached (stable for next few requests)
    - Last few turns + new message: NOT cached (changing)

    This is especially valuable in long analysis sessions where the user
    asks many questions about the same document.
    """

    # Calculate cache boundary
    cache_boundary_idx = min(len(conversation_history), cache_history_turns * 2)
    cached_history = conversation_history[:cache_boundary_idx]
    live_history = conversation_history[cache_boundary_idx:]

    # Apply cache_control to the last message in the cacheable history
    if cached_history:
        last_cached = cached_history[-1]
        # Wrap the last message's content in a cacheable block
        if isinstance(last_cached.get("content"), str):
            cached_history[-1] = {
                **last_cached,
                "content": [{
                    "type": "text",
                    "text": last_cached["content"],
                    "cache_control": {"type": "ephemeral"}
                }]
            }

    # Combine: cached history + live history + new message
    all_messages = (
        cached_history +
        live_history +
        [{"role": "user", "content": new_user_message}]
    )

    return {
        "system": [{
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"}
        }],
        "messages": all_messages
    }

# Usage in a chat application:
class CachedChatSession:
    """
    Chat session with automatic conversation caching.
    """

    def __init__(self, system_prompt: str, model: str = "claude-sonnet-4-6"):
        self.system_prompt = system_prompt
        self.model = model
        self.history: list[dict] = []
        self.total_tokens_saved = 0

    def chat(self, user_message: str, max_tokens: int = 1024) -> str:
        """Send a message and get a response, with automatic caching."""
        request = build_multi_turn_cached_request(
            system_prompt=self.system_prompt,
            conversation_history=self.history,
            new_user_message=user_message,
            cache_history_turns=8
        )

        response = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            **request
        )

        # Track savings
        cache_hit = getattr(response.usage, "cache_read_input_tokens", 0)
        self.total_tokens_saved += cache_hit

        # Update history
        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": response.content[0].text})

        return response.content[0].text
```

---

## 7. Tool Definition Caching

Tool schemas rarely change between requests. Cache them to save significant tokens in agent applications.

```python
# Tool definitions can add 200–500 tokens per tool
# With 8 tools: 1,600–4,000 extra input tokens on EVERY call
# Cache them!

TOOL_DEFINITIONS = [
    {"name": "search_wine_list", "description": "...", "input_schema": {...}},
    {"name": "search_food_menu", "description": "...", "input_schema": {...}},
    {"name": "get_table_availability", "description": "...", "input_schema": {...}},
    # ... more tools
]

# To cache tool definitions, include them in the system prompt as a text block:
import json

def build_system_with_cached_tools(
    persona_prompt: str,
    tool_definitions: list[dict]
) -> list[dict]:
    """
    Embed tool definitions in the cached system prompt block.
    This is more cache-efficient than passing tools in the API's tools parameter
    when tools are completely static.

    Note: When using this pattern, you still pass tools= to the API
    (for Claude to be able to call them), but the heavy descriptions
    are pre-processed via the cached system block.
    """
    tool_summary = "AVAILABLE TOOLS:\n"
    for tool in tool_definitions:
        tool_summary += f"- {tool['name']}: {tool['description'][:100]}...\n"

    return [
        {
            "type": "text",
            "text": persona_prompt + "\n\n" + tool_summary,
            "cache_control": {"type": "ephemeral"}
        }
    ]
```

---

## 8. ROI Calculation

```python
def calculate_cache_roi(
    requests_per_day: int,
    stable_tokens: int,           # Tokens in cached content
    dynamic_tokens_avg: int,      # Average tokens unique per request
    output_tokens_avg: int = 400, # Average output tokens
    model: str = "claude-sonnet-4-6",
    cache_hit_rate: float = 0.95  # Realistic hit rate (95% on busy systems)
) -> dict:
    """
    Calculate the monthly ROI of enabling prompt caching.

    Args:
        requests_per_day: Daily request volume
        stable_tokens: Tokens that are the same across requests (cacheable)
        dynamic_tokens_avg: Tokens unique to each request
        output_tokens_avg: Average response length in tokens
        model: Which model to calculate for
        cache_hit_rate: Expected cache hit rate (0.0–1.0)
    """
    p = PRICING[model]

    # WITHOUT caching (all input at normal rate)
    daily_no_cache = requests_per_day * (
        (stable_tokens + dynamic_tokens_avg) / 1_000_000 * p["normal_input"]
        + output_tokens_avg / 1_000_000 * p["output_per_mtok"]
    )

    # WITH caching
    # Cache writes: first request + re-writes after TTL expires
    # Assume cache expires once per 5-minute window (12× per hour)
    writes_per_day = max(1, 24 * 12)  # At most once per 5 min
    writes_per_day = min(writes_per_day, requests_per_day)  # Can't write more than requests
    cache_write_cost = writes_per_day * stable_tokens / 1_000_000 * p["cache_write"]

    # Cache reads: all requests minus writes
    cache_reads = int(requests_per_day * cache_hit_rate)
    cache_read_cost = cache_reads * stable_tokens / 1_000_000 * p["cache_read"]

    # Uncached dynamic tokens
    dynamic_cost = requests_per_day * dynamic_tokens_avg / 1_000_000 * p["normal_input"]
    output_cost = requests_per_day * output_tokens_avg / 1_000_000 * p["output_per_mtok"]

    daily_with_cache = cache_write_cost + cache_read_cost + dynamic_cost + output_cost
    daily_savings = daily_no_cache - daily_with_cache
    savings_pct = daily_savings / daily_no_cache * 100 if daily_no_cache > 0 else 0

    return {
        "model": model,
        "requests_per_day": requests_per_day,
        "stable_tokens": stable_tokens,
        "daily_cost_no_cache_usd": round(daily_no_cache, 4),
        "daily_cost_with_cache_usd": round(daily_with_cache, 4),
        "daily_savings_usd": round(daily_savings, 4),
        "monthly_savings_usd": round(daily_savings * 30, 2),
        "annual_savings_usd": round(daily_savings * 365, 2),
        "savings_pct": round(savings_pct, 1),
        "breakeven_requests": 2,    # Always worth it after 2 requests
        "hit_rate_assumption": f"{cache_hit_rate*100:.0f}%"
    }

# Real-world examples:
print("\n--- Restaurant AI (1,000 req/day, 8K stable tokens) ---")
result = calculate_cache_roi(1_000, 8_000, 200)
print(f"Monthly savings: ${result['monthly_savings_usd']} ({result['savings_pct']}% reduction)")

print("\n--- High-traffic app (50,000 req/day, 5K stable tokens) ---")
result = calculate_cache_roi(50_000, 5_000, 150)
print(f"Monthly savings: ${result['monthly_savings_usd']} ({result['savings_pct']}% reduction)")

print("\n--- Document analysis (100 req/day, 50K token document) ---")
result = calculate_cache_roi(100, 50_000, 200)
print(f"Monthly savings: ${result['monthly_savings_usd']} ({result['savings_pct']}% reduction)")
```

---

## 9. Monitoring Cache Performance

```python
from collections import defaultdict
from dataclasses import dataclass, field

@dataclass
class CacheMetrics:
    """Track cache performance across all API calls."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_stable_tokens: int = 0
    total_tokens_cached: int = 0
    total_tokens_written: int = 0
    total_cost_no_cache: float = 0.0
    total_cost_with_cache: float = 0.0

    def record_response(self, response, model: str = "claude-sonnet-4-6"):
        p = PRICING[model]
        usage = response.usage
        input_tok = usage.input_tokens
        output_tok = usage.output_tokens
        cache_read = getattr(usage, "cache_read_input_tokens", 0)
        cache_write = getattr(usage, "cache_creation_input_tokens", 0)

        self.total_requests += 1
        if cache_read > 0:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

        self.total_tokens_cached += cache_read
        self.total_tokens_written += cache_write

        # Actual cost (with caching)
        uncached_input = input_tok - cache_read
        actual_cost = (
            uncached_input / 1_000_000 * p["normal_input"]
            + cache_write / 1_000_000 * p["cache_write"]
            + cache_read / 1_000_000 * p["cache_read"]
            + output_tok / 1_000_000 * p["output_per_mtok"]
        )
        self.total_cost_with_cache += actual_cost

        # Hypothetical cost without caching
        no_cache_cost = (
            input_tok / 1_000_000 * p["normal_input"]
            + output_tok / 1_000_000 * p["output_per_mtok"]
        )
        self.total_cost_no_cache += no_cache_cost

    @property
    def hit_rate(self) -> float:
        return self.cache_hits / self.total_requests if self.total_requests else 0

    @property
    def savings_usd(self) -> float:
        return self.total_cost_no_cache - self.total_cost_with_cache

    @property
    def savings_pct(self) -> float:
        return (self.savings_usd / self.total_cost_no_cache * 100
                if self.total_cost_no_cache else 0)

    def report(self) -> str:
        return (
            f"Cache Performance Report:\n"
            f"  Total requests:   {self.total_requests:,}\n"
            f"  Hit rate:         {self.hit_rate:.1%}\n"
            f"  Tokens saved:     {self.total_tokens_cached:,}\n"
            f"  Cost with cache:  ${self.total_cost_with_cache:.4f}\n"
            f"  Cost without:     ${self.total_cost_no_cache:.4f}\n"
            f"  Total savings:    ${self.savings_usd:.4f} ({self.savings_pct:.1f}%)"
        )

# Global metrics tracker
cache_metrics = CacheMetrics()

# Log after every API call:
response = client.messages.create(...)
cache_metrics.record_response(response)

# Print report periodically:
print(cache_metrics.report())
```

---

## 10. Junior Quick-Start Walkthrough

**Goal**: Enable prompt caching in 5 minutes and see immediate savings.

**Step 1**: Check if your system prompt is long enough to cache.

```python
import anthropic
client = anthropic.Anthropic()

# Count your system prompt tokens
my_system_prompt = "You are a helpful assistant. [your full prompt here]"
count = client.messages.count_tokens(
    model="claude-sonnet-4-6",
    system=my_system_prompt,
    messages=[{"role": "user", "content": "hi"}]
)
print(f"System prompt tokens: {count.input_tokens}")
# If > 1024 tokens → caching is worth it
# If < 1024 tokens → either expand your prompt or skip caching
```

**Step 2**: Enable caching by changing how you pass the system prompt.

```python
# Before (no caching):
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system="Your system prompt...",    # ← Plain string, NOT cached
    messages=[{"role": "user", "content": user_message}]
)

# After (with caching) — just wrap it in a list of blocks:
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=[{                           # ← List of content blocks
        "type": "text",
        "text": "Your system prompt...",
        "cache_control": {"type": "ephemeral"}  # ← This line enables caching
    }],
    messages=[{"role": "user", "content": user_message}]
)
```

**Step 3**: Verify it's working.

```python
# Check the response for cache metrics:
print(f"Cache write: {response.usage.cache_creation_input_tokens}")
# First request: this should be > 0 (cache written)

# Send a second request with the SAME system prompt:
response2 = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=[{"type": "text", "text": "Your system prompt...", "cache_control": {"type": "ephemeral"}}],
    messages=[{"role": "user", "content": "different question"}]
)
print(f"Cache read: {response2.usage.cache_read_input_tokens}")
# This should be > 0 (cache hit! paying 0.10× instead of 1×)
```

---

## 11. Senior Patterns and Production Hardening

### Cache Key Management

The cache key is determined by the exact content of the cached block. Even a single character difference creates a cache miss.

```python
class CacheKeyManager:
    """
    Ensure cache stability by normalising content before caching.
    Prevents accidental cache busts from whitespace or encoding differences.
    """

    @staticmethod
    def normalise(text: str) -> str:
        """
        Normalise text to maximise cache hit rate.
        - Strip trailing whitespace
        - Normalise line endings
        - Ensure consistent encoding
        """
        # Normalise line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Strip trailing whitespace per line
        lines = [line.rstrip() for line in text.split("\n")]
        # Remove trailing empty lines
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines)

    @staticmethod
    def hash(text: str) -> str:
        """Generate a hash of the cache key for logging."""
        import hashlib
        return hashlib.sha256(text.encode()).hexdigest()[:12]

# Usage:
manager = CacheKeyManager()
normalised_prompt = manager.normalise(SYSTEM_PROMPT)
print(f"Cache key fingerprint: {manager.hash(normalised_prompt)}")
# Log this with each request — same fingerprint = same cache key
```

### Cache-Aware Deployment Pattern

```python
# When deploying a new system prompt version:
# 1. Old version is cached on Anthropic servers
# 2. New version creates a new cache entry (new key)
# 3. Transition period: some requests hit old cache, some write new
# 4. After 5 minutes: old cache expires, all requests use new cache

# Best practice: version your system prompts
SYSTEM_PROMPT_V3 = """v3.0 — 2026-05-22
You are Maître...
"""

SYSTEM_PROMPT_V2 = """v2.1 — 2026-04-10
You are Maître...
"""

# Log which version is in use
def make_request_with_versioned_prompt(version: str, user_message: str):
    prompt = SYSTEM_PROMPT_V3 if version == "v3" else SYSTEM_PROMPT_V2

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=[{"type": "text", "text": prompt, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_message}]
    )

    # Log version + cache status for debugging
    cache_hit = getattr(response.usage, "cache_read_input_tokens", 0) > 0
    logger.info(f"prompt_version={version} cache_hit={cache_hit}")

    return response
```

---

## 12. Tips, Tricks and Gotchas

**Tip 1 — Cache large knowledge documents, not just system prompts.** A 10,000-token policy document cached saves far more than a 500-token system prompt. The ROI scales with stable token count.

**Tip 2 — Cache tool definitions when they're static.** If your tools never change between requests (common for production apps), include them as cached content blocks.

**Tip 3 — Monitor `cache_creation_input_tokens` in production.** A high number means your cache is expiring frequently. Either increase request frequency or add warming.

**Tip 4 — Batch processing + caching = maximum savings.** Use the Message Batches API (50% off) with cached prompts (90% off stable tokens) for offline workloads. Combined savings can exceed 90%.

**Tip 5 — The first request in a session costs MORE (cache write is 1.25×).** For very-low-traffic endpoints with large prompts, calculate whether total caching still pays off vs. never caching.

**Gotcha 1 — Cache key is the entire content, not just a hash.** Any change to the cached block — including extra spaces, different encoding, or reordering — creates a different cache key and a miss.

**Gotcha 2 — Tool schemas passed in the `tools=` parameter ARE included in the cache key.** If you change a tool definition between requests, it invalidates the cached prefix.

**Gotcha 3 — Multiple `cache_control` blocks don't all cache independently.** You can have up to 4 cache breakpoints. The cache prefix extends from the start to the LAST cache_control marker before any dynamic content.

**Gotcha 4 — `ephemeral` is the only supported cache type.** There's currently no "permanent" cache. All caches expire after 5 minutes of inactivity.

**Gotcha 5 — Cache warming has a cost.** Each warming request writes tokens at 1.25× the normal price. Calculate whether warming cost < caching savings for your traffic pattern.

---

## 13. Quick Reference Cheatsheet

```
CACHE PRICING:
  Cache write:  1.25× normal input price (one-time cost to populate)
  Cache read:   0.10× normal input price (90% discount on hits)
  Cache TTL:    ~5 minutes of inactivity

MINIMUM REQUIREMENTS:
  Min cacheable tokens: 1,024 (below this = no caching)
  Max cache breakpoints: 4 per request

SYNTAX:
  {"type": "text", "text": "...", "cache_control": {"type": "ephemeral"}}

PLACEMENT RULE (critical!):
  ✓ [CACHED: static content] → [NOT cached: dynamic content]
  ✗ [NOT cached: dynamic] → [CACHED: static]  ← cache ineffective!

ROI RULE OF THUMB:
  If stable_tokens > 1,024 AND requests > 1/day → ALWAYS cache
  Savings increase linearly with: stable token count × request volume

WHAT TO CACHE:
  ✓ System prompts (>1K tokens)
  ✓ Knowledge documents (>1K tokens)
  ✓ Tool definitions (stable)
  ✓ Few-shot examples (stable)
  ✗ User messages
  ✗ RAG-retrieved chunks
  ✗ Real-time data

MONITORING:
  response.usage.cache_creation_input_tokens → tokens written (new cache)
  response.usage.cache_read_input_tokens     → tokens read (cache hit)
  hit_rate = hits / total_requests           → target >90% for active apps

WARMING TRIGGER:
  Warm if: requests_per_hour < 12 (less than 1 request per 5 minutes)
  Warm every: 240 seconds (4 minutes before 5-minute TTL)
  Warming model: Use Haiku for cheapest warming cost
```
