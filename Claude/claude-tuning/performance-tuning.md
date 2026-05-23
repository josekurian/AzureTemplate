# performance-tuning.md — Latency and Throughput Optimization

> **Purpose**: Comprehensive techniques to reduce response latency, increase throughput, and optimize Claude's production performance. Covers measurement, caching, concurrency, streaming, tool optimization, and monitoring targets with real production values.
> **Who This Is For**: Junior developers learning production patterns, senior engineers tuning high-traffic systems.
> **Owner**: jose@hybridgenai.com

---

## Navigation

1. [Latency Decomposition and Measurement](#1-latency-decomposition-and-measurement)
2. [Reducing Time-to-First-Token (TTFT)](#2-reducing-time-to-first-token-ttft)
3. [Streaming for Perceived Performance](#3-streaming-for-perceived-performance)
4. [Parallelism and Concurrency](#4-parallelism-and-concurrency)
5. [Prompt Construction Performance](#5-prompt-construction-performance)
6. [Application-Layer Response Caching](#6-application-layer-response-caching)
7. [Tool Execution Optimization](#7-tool-execution-optimization)
8. [Connection and HTTP Optimization](#8-connection-and-http-optimization)
9. [Model Selection for Latency](#9-model-selection-for-latency)
10. [Performance Monitoring and Alerting](#10-performance-monitoring-and-alerting)
11. [Junior Walkthrough — First Performance Audit](#11-junior-walkthrough--first-performance-audit)
12. [Senior Patterns — High-Traffic Production](#12-senior-patterns--high-traffic-production)
13. [Tips, Tricks, and Gotchas](#13-tips-tricks-and-gotchas)
14. [Quick Reference Cheatsheet](#14-quick-reference-cheatsheet)

---

## 1. Latency Decomposition and Measurement

Understanding where time is spent is the prerequisite to reducing it. Before optimizing, **measure first**.

```
Total Latency = Network RTT (client ↔ Anthropic API)
              + Time-to-First-Token (TTFT)    ← Grows with prompt length
              + Token Generation Time          ← Grows with output length
              + Tool Execution Time            ← Depends on your tools
              + Response Deserialization       ← Usually negligible

Typical values (Claude Sonnet 4, US East, 2026):
  Network RTT:           20 – 80 ms  (depends on geography)
  TTFT (uncached):      500 – 2,000 ms  (grows ~1ms per 100 input tokens)
  TTFT (cached):        200 – 600 ms   (cached prefill is skipped)
  Token Generation:     ~80-120 tokens/sec (streaming mode)
  Tool Call (DB query): 50 – 500 ms
  Tool Call (web fetch): 500 – 3,000 ms
```

### Latency Measurement Harness

```python
import time
import anthropic
from dataclasses import dataclass, field
from typing import Optional
import statistics

@dataclass
class LatencyMeasurement:
    """Full latency breakdown for a single API call."""
    request_id: str
    model: str
    prompt_tokens: int
    output_tokens: int
    total_latency_ms: float
    ttft_ms: Optional[float]       # None if not streaming
    generation_ms: Optional[float] # Time from first to last token
    tool_calls: int = 0
    tool_latency_ms: float = 0.0
    cache_hit: bool = False

class LatencyProfiler:
    """
    Measure and report Claude API latency with full breakdown.
    
    Usage:
        profiler = LatencyProfiler()
        result, measurement = profiler.measure(model="claude-sonnet-4-6",
                                               max_tokens=512,
                                               messages=[...])
    """
    
    def __init__(self, client: anthropic.Anthropic):
        self.client = client
        self.measurements: list[LatencyMeasurement] = []
    
    def measure_streaming(self, **kwargs) -> tuple[str, LatencyMeasurement]:
        """Measure streaming call with TTFT tracking."""
        start = time.perf_counter()
        first_token_time: Optional[float] = None
        full_text = ""
        
        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                if first_token_time is None:
                    first_token_time = time.perf_counter()
                full_text += text
            
            final = stream.get_final_message()
        
        end = time.perf_counter()
        
        ttft_ms = (first_token_time - start) * 1000 if first_token_time else None
        total_ms = (end - start) * 1000
        gen_ms = (end - first_token_time) * 1000 if first_token_time else None
        
        m = LatencyMeasurement(
            request_id=final.id,
            model=kwargs.get("model", "unknown"),
            prompt_tokens=final.usage.input_tokens,
            output_tokens=final.usage.output_tokens,
            total_latency_ms=total_ms,
            ttft_ms=ttft_ms,
            generation_ms=gen_ms,
            cache_hit=final.usage.cache_read_input_tokens > 0 if hasattr(final.usage, 'cache_read_input_tokens') else False,
        )
        self.measurements.append(m)
        return full_text, m
    
    def p50_p95_p99(self, metric: str = "total_latency_ms") -> dict:
        """Calculate percentile latencies over collected measurements."""
        values = sorted(getattr(m, metric) for m in self.measurements if getattr(m, metric) is not None)
        if not values:
            return {}
        return {
            "p50": statistics.median(values),
            "p95": values[int(len(values) * 0.95)],
            "p99": values[int(len(values) * 0.99)],
            "min": values[0],
            "max": values[-1],
            "count": len(values),
        }
    
    def report(self) -> dict:
        """Full performance report."""
        return {
            "total_latency": self.p50_p95_p99("total_latency_ms"),
            "ttft": self.p50_p95_p99("ttft_ms"),
            "generation": self.p50_p95_p99("generation_ms"),
            "cache_hit_rate": sum(1 for m in self.measurements if m.cache_hit) / max(len(self.measurements), 1),
        }
```

### Why TTFT Grows With Prompt Length

```
# Empirical approximation (Sonnet 4):
# TTFT ≈ BASE_LATENCY + (prompt_tokens × 0.005) ms

BASE_LATENCY_MS = 400  # Network + model initialization

examples:
  1,000  tokens → 400 + 5   = ~405 ms TTFT
  5,000  tokens → 400 + 25  = ~425 ms TTFT
  20,000 tokens → 400 + 100 = ~500 ms TTFT
  50,000 tokens → 400 + 250 = ~650 ms TTFT
 200,000 tokens → 400 + 1000= ~1,400 ms TTFT

# ✅ TTFT is less sensitive to prompt length than most people expect
# ❌ Myth: "200K context window means huge TTFT" — not true with caching
```

---

## 2. Reducing Time-to-First-Token (TTFT)

### 2.1 Prompt Caching (Biggest TTFT Win)

Cached prompts skip the prefill computation. TTFT drops by 30–70% on cache hits.

```python
import anthropic
import os

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ──────────────────────────────────────────────────────────────
# STABLE content → cache it (5-minute TTL, 0.1× cost on re-read)
# ──────────────────────────────────────────────────────────────
LUMIERE_SYSTEM_PROMPT = """
You are Maître, the AI concierge for Lumière, a Michelin-starred restaurant in London.
[... 2,000 tokens of stable restaurant context ...]
"""

WINE_LIST = """
<wine_list>
[... 3,000 tokens of wine catalogue ...]
</wine_list>
"""

def build_cached_request(user_question: str, dynamic_context: str = "") -> dict:
    """
    Build a request where the stable parts are cached.
    
    Cache boundary rules:
    - Put large, stable content FIRST (before dynamic content)
    - Mark it with cache_control: {"type": "ephemeral"}
    - The LAST cache_control marker is the actual cache breakpoint
    
    With 5,000 cached tokens:
    - First request:  normal TTFT (cache write)
    - Subsequent:     ~40% faster TTFT (cache read)
    """
    messages = [
        {
            "role": "user",
            "content": [
                # ✅ Large stable context — CACHE THIS
                {
                    "type": "text",
                    "text": WINE_LIST,
                    "cache_control": {"type": "ephemeral"}  # Cache breakpoint here
                },
                # ✅ Optional: semi-stable dynamic context
                {
                    "type": "text",
                    "text": dynamic_context,
                    # No cache_control on dynamic content — it changes per request
                } if dynamic_context else None,
                # ✅ The actual user question (always unique)
                {
                    "type": "text",
                    "text": user_question
                },
            ]
        }
    ]
    # Remove None entries
    messages[0]["content"] = [c for c in messages[0]["content"] if c]
    
    return {
        "model": "claude-sonnet-4-6",
        "max_tokens": 512,
        "system": [
            {
                "type": "text",
                "text": LUMIERE_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"}  # Cache system prompt too
            }
        ],
        "messages": messages,
    }

# First call: cache miss (writes cache)
response1 = client.messages.create(**build_cached_request("What red wines under £60 do you have?"))
print(f"Cache write: {response1.usage.cache_creation_input_tokens} tokens cached")

# Second call: cache hit (~40% faster TTFT)
response2 = client.messages.create(**build_cached_request("Recommend a wine for the tasting menu."))
print(f"Cache read: {response2.usage.cache_read_input_tokens} tokens from cache")
```

### 2.2 Reduce Prompt Length

Every 1,000 tokens of prompt = ~5ms extra TTFT. Compress where possible.

```python
# ❌ Verbose prompt (1,200 tokens)
VERBOSE_PROMPT = """
You are a helpful restaurant assistant named Maître. You work at Lumière restaurant.
Your job is to help guests with their questions. You should be polite and professional.
Always try to be helpful. If you don't know something, say so. 
Be concise but thorough in your responses...
[continues for 1,000 more tokens of instructions]
"""

# ✅ Compressed equivalent (300 tokens)
CONCISE_PROMPT = """
You are Maître, concierge AI for Lumière restaurant (Michelin-starred, London).
Be warm, knowledgeable, and concise. Only answer restaurant-related questions.
Allergen info: always add "Confirm with server before ordering."
Out of scope: refer to staff.
"""

# Savings: 900 tokens × ~$0.000003/token = ~$0.0027 per request
# At 10,000 requests/day = $27/day = $810/month saved on TTFT AND cost
```

### 2.3 Quantify Your TTFT Budget

```python
# Define TTFT budget per user-facing path
TTFT_BUDGET_MS = {
    "chat_widget":     800,   # User is waiting, interactive
    "inline_suggest":  400,   # Autocomplete, very latency-sensitive
    "background_task": 5000,  # User not watching, can be slow
    "batch_analysis":  None,  # No TTFT constraint — async
}

def select_model_for_latency(path: str) -> str:
    """Choose model based on TTFT budget."""
    budget = TTFT_BUDGET_MS.get(path, 2000)
    
    if budget is None or budget > 3000:
        return "claude-sonnet-4-6"    # Quality over speed
    elif budget > 800:
        return "claude-sonnet-4-6"    # Sonnet is fast enough for most paths
    else:
        return "claude-haiku-4-5-20251001"  # Haiku for tight TTFT budgets
```

---

## 3. Streaming for Perceived Performance

Streaming does NOT reduce total latency. It dramatically improves **perceived** latency — the user sees the first word in <1s even if the full response takes 5s.

### 3.1 Synchronous Streaming (Simple Use Cases)

```python
def stream_response(question: str, system: str) -> str:
    """
    Stream response and print to terminal.
    Returns full text when complete.
    
    Args:
        question: User's question
        system: System prompt
    
    Returns:
        Complete response text
    """
    full_text = ""
    
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": question}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)  # flush=True is CRITICAL
            full_text += text
        
        # Always capture final message for token usage tracking
        final = stream.get_final_message()
        print(f"\n\n[Tokens: {final.usage.input_tokens}→{final.usage.output_tokens}]")
    
    return full_text
```

### 3.2 Async Streaming for Web APIs (FastAPI + SSE)

```python
import asyncio
import json
import anthropic
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

client = anthropic.AsyncAnthropic()
app = FastAPI()

@app.get("/api/chat/stream")
async def stream_chat(question: str, guest_id: str = ""):
    """
    Server-Sent Events endpoint for streaming Claude responses.
    
    Frontend connects with:
        const es = new EventSource('/api/chat/stream?question=...')
        es.onmessage = (e) => { if (e.data !== '[DONE]') appendText(JSON.parse(e.data).text) }
    """
    async def generate():
        try:
            # Load guest memory (fast, in-memory or Redis)
            memory = await load_guest_memory(guest_id) if guest_id else ""
            
            system = build_system_prompt(memory)
            
            async with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=512,
                system=system,
                messages=[{"role": "user", "content": question}],
            ) as stream:
                async for text in stream.text_stream:
                    # SSE format: "data: {json}\n\n"
                    yield f"data: {json.dumps({'text': text, 'done': False})}\n\n"
                
                # Signal completion with usage stats
                final = await stream.get_final_message()
                yield f"data: {json.dumps({'done': True, 'usage': {'input': final.usage.input_tokens, 'output': final.usage.output_tokens}})}\n\n"
                yield "data: [DONE]\n\n"
        
        except anthropic.RateLimitError:
            yield f"data: {json.dumps({'error': 'Service busy. Please try again.', 'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': 'An error occurred.', 'done': True})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )

# ── WebSocket alternative for bidirectional streaming ──────────────────────
from fastapi import WebSocket

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket for two-way streaming — better for chat UIs.
    Supports multiple messages in same connection.
    """
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            question = data.get("question", "")
            
            async with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=512,
                messages=[{"role": "user", "content": question}],
            ) as stream:
                async for text in stream.text_stream:
                    await websocket.send_json({"type": "token", "text": text})
                
                final = await stream.get_final_message()
                await websocket.send_json({
                    "type": "done",
                    "usage": {
                        "input": final.usage.input_tokens,
                        "output": final.usage.output_tokens
                    }
                })
    
    except Exception:
        await websocket.close()
```

### 3.3 React Frontend Integration

```javascript
// hooks/useClaudeStream.js
import { useState, useCallback, useRef } from 'react';

export function useClaudeStream() {
    const [text, setText] = useState('');
    const [isStreaming, setIsStreaming] = useState(false);
    const [isWaiting, setIsWaiting] = useState(false); // Waiting for first token
    const [error, setError] = useState(null);
    const esRef = useRef(null);
    
    const ask = useCallback((question) => {
        // Reset state
        setText('');
        setError(null);
        setIsWaiting(true);   // Show typing indicator
        setIsStreaming(false);
        
        // Close any existing stream
        if (esRef.current) esRef.current.close();
        
        const url = `/api/chat/stream?question=${encodeURIComponent(question)}`;
        const es = new EventSource(url);
        esRef.current = es;
        
        es.onmessage = (event) => {
            if (event.data === '[DONE]') {
                es.close();
                setIsStreaming(false);
                setIsWaiting(false);
                return;
            }
            
            const data = JSON.parse(event.data);
            
            if (data.error) {
                setError(data.error);
                setIsStreaming(false);
                setIsWaiting(false);
                es.close();
                return;
            }
            
            if (data.text) {
                setIsWaiting(false);     // First token arrived — hide typing indicator
                setIsStreaming(true);
                setText(prev => prev + data.text);
            }
        };
        
        es.onerror = () => {
            setError('Connection lost. Please try again.');
            setIsStreaming(false);
            setIsWaiting(false);
            es.close();
        };
    }, []);
    
    const stop = useCallback(() => {
        if (esRef.current) esRef.current.close();
        setIsStreaming(false);
        setIsWaiting(false);
    }, []);
    
    return { text, isStreaming, isWaiting, error, ask, stop };
}

// Component usage:
function ChatWidget() {
    const { text, isStreaming, isWaiting, error, ask } = useClaudeStream();
    
    return (
        <div>
            {isWaiting && <TypingIndicator />}        {/* Show dots while waiting for first token */}
            {text && <ResponseText text={text} />}    {/* Show streaming text */}
            {isStreaming && <StopButton />}           {/* Allow user to stop mid-stream */}
            {error && <ErrorBanner message={error} />}
        </div>
    );
}
```

---

## 4. Parallelism and Concurrency

### 4.1 Async Parallel Requests

```python
import asyncio
from typing import List

client_async = anthropic.AsyncAnthropic()

async def analyse_invoice(invoice_text: str, index: int) -> dict:
    """Analyse a single invoice."""
    response = await client_async.messages.create(
        model="claude-haiku-4-5-20251001",  # Haiku for speed + cost
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": f"Extract: vendor_name, date, total, currency from:\n{invoice_text[:2000]}\nReturn JSON only."
        }]
    )
    return {"index": index, "result": json.loads(response.content[0].text)}

async def analyse_all_invoices_parallel(invoices: List[str]) -> List[dict]:
    """
    Process all invoices concurrently.
    
    Sequential: 10 invoices × 2s each = 20s
    Parallel:   10 invoices × 2s each = ~2s (limited by slowest)
    
    Args:
        invoices: List of invoice text strings
    
    Returns:
        List of extraction results in original order
    """
    tasks = [analyse_invoice(inv, i) for i, inv in enumerate(invoices)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Separate successes from errors
    successes = [r for r in results if not isinstance(r, Exception)]
    errors = [r for r in results if isinstance(r, Exception)]
    
    if errors:
        print(f"Warning: {len(errors)} invoices failed: {[str(e) for e in errors]}")
    
    return sorted(successes, key=lambda x: x["index"])

# Run it
async def main():
    invoices = load_todays_invoices()  # Load from Azure Blob Storage
    results = await analyse_all_invoices_parallel(invoices)
    print(f"Processed {len(results)} invoices in parallel")

asyncio.run(main())
```

### 4.2 Rate-Limited Concurrent Client

When volume exceeds API rate limits, control concurrency carefully.

```python
import asyncio
from asyncio import Semaphore
import time
from collections import deque

class RateLimitedClaudeClient:
    """
    Async client with:
    - Concurrent request cap (max_concurrent)
    - Requests-per-minute cap (rpm_limit)
    - Tokens-per-minute tracking (tpm_limit)
    
    Default settings match Anthropic's Tier 2 limits.
    
    Args:
        max_concurrent:   Max simultaneous in-flight requests (default: 10)
        rpm_limit:        Max requests per minute (default: 50)
        tpm_limit:        Max tokens per minute (default: 100,000)
    """
    
    def __init__(
        self,
        max_concurrent: int = 10,
        rpm_limit: int = 50,
        tpm_limit: int = 100_000,
    ):
        self.semaphore = Semaphore(max_concurrent)
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self._request_timestamps: deque = deque()
        self._token_timestamps: deque = deque()  # (timestamp, tokens)
        self._client = anthropic.AsyncAnthropic()
    
    async def create(self, **kwargs) -> anthropic.types.Message:
        """Thread-safe create with rate limiting."""
        async with self.semaphore:
            await self._wait_for_rpm_quota()
            response = await self._client.messages.create(**kwargs)
            total_tokens = response.usage.input_tokens + response.usage.output_tokens
            self._token_timestamps.append((time.monotonic(), total_tokens))
            return response
    
    async def _wait_for_rpm_quota(self):
        """Block until RPM quota allows this request."""
        while True:
            now = time.monotonic()
            
            # Purge timestamps older than 60 seconds
            while self._request_timestamps and now - self._request_timestamps[0] > 60:
                self._request_timestamps.popleft()
            
            if len(self._request_timestamps) < self.rpm_limit:
                self._request_timestamps.append(now)
                return
            
            # Calculate wait time until oldest request falls out of window
            wait = 60.0 - (now - self._request_timestamps[0]) + 0.05
            await asyncio.sleep(wait)

# Usage example
limited_client = RateLimitedClaudeClient(max_concurrent=10, rpm_limit=50)

async def process_batch(items: list) -> list:
    """Process many items while respecting rate limits."""
    tasks = [limited_client.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[{"role": "user", "content": f"Classify: {item}"}],
    ) for item in items]
    
    results = await asyncio.gather(*tasks)
    return [r.content[0].text for r in results]
```

### 4.3 Thread Pool for CPU-Bound Pre/Post Processing

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

def preprocess_document(doc: dict) -> dict:
    """CPU-heavy preprocessing (OCR, parsing, etc.)"""
    # ... text extraction, normalization, chunking
    return {"id": doc["id"], "text": extract_text(doc)}

def run_preprocessing_pipeline(documents: list) -> list:
    """
    Preprocess documents in parallel using thread pool.
    Then call Claude in parallel for all preprocessed docs.
    
    Phase 1: CPU-bound preprocessing (thread pool)
    Phase 2: IO-bound Claude calls (async)
    """
    # Phase 1: Parallel preprocessing
    preprocessed = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_doc = {executor.submit(preprocess_document, doc): doc for doc in documents}
        for future in as_completed(future_to_doc):
            result = future.result()
            preprocessed.append(result)
    
    # Phase 2: Parallel Claude calls
    async def run_async():
        tasks = [
            client_async.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=400,
                messages=[{"role": "user", "content": f"Summarize:\n{doc['text'][:3000]}"}]
            )
            for doc in preprocessed
        ]
        return await asyncio.gather(*tasks)
    
    responses = asyncio.run(run_async())
    return [r.content[0].text for r in responses]
```

---

## 5. Prompt Construction Performance

### 5.1 Pre-Compile Templates at Startup

String formatting is cheap but non-trivial at high volume. Pre-compile everything.

```python
from string import Template
import re

# ── Pre-compile at module import time (once) ──────────────────────────────
_CHAT_TEMPLATE = Template("""$persona

<memory>
$memory
</memory>

<context>
$context
</context>

$question""")

_EXTRACTION_TEMPLATE = Template("""Extract the following fields from the text below.
Return valid JSON matching this schema: $schema

Text:
$text""")

# ── Per-request: fast substitution only ──────────────────────────────────
def build_chat_message(
    persona: str,
    memory: str,
    context: str,
    question: str,
) -> str:
    """
    Build chat message from pre-compiled template.
    ~10× faster than f-string on complex prompts.
    """
    return _CHAT_TEMPLATE.substitute(
        persona=persona,
        memory=memory or "No prior memory.",
        context=context or "No additional context.",
        question=question,
    )

def build_extraction_message(schema: str, text: str) -> str:
    return _EXTRACTION_TEMPLATE.substitute(schema=schema, text=text[:4000])
```

### 5.2 Lazy Loading of Static Content

```python
import functools
import json
from pathlib import Path

class PromptAssets:
    """
    Lazy-load prompt assets on first use.
    Prevents slow startup and ensures assets are current.
    
    Assets are loaded once and cached for the lifetime of the process.
    In production, use a cache TTL or re-deploy to update assets.
    """
    
    @functools.cached_property
    def wine_list(self) -> str:
        """Load wine list from file (heavy, ~3,000 tokens). Loaded once."""
        path = Path("data/wine_list.txt")
        return path.read_text() if path.exists() else ""
    
    @functools.cached_property  
    def menu(self) -> str:
        """Load current menu."""
        return Path("data/menu.txt").read_text()
    
    @functools.cached_property
    def staff_training(self) -> str:
        """Load staff training guidelines."""
        return Path("data/staff_training.txt").read_text()
    
    def invalidate(self):
        """Clear cache to reload from disk (call after menu updates)."""
        for attr in ["wine_list", "menu", "staff_training"]:
            if attr in self.__dict__:
                del self.__dict__[attr]

# Global instance — loaded once per process
assets = PromptAssets()
```

---

## 6. Application-Layer Response Caching

Cache identical API responses to avoid redundant Claude calls entirely.

### 6.1 In-Memory Cache (Development / Low Traffic)

```python
import hashlib
import time
from threading import Lock
from dataclasses import dataclass
from typing import Optional

@dataclass
class CacheEntry:
    response: str
    created_at: float
    hits: int = 0

class ResponseCache:
    """
    Thread-safe in-memory response cache with TTL.
    
    For production, replace with Redis:
        redis_client.setex(key, ttl, json.dumps(response))
    
    Args:
        ttl_seconds:   How long to keep cached responses (default: 3600 = 1 hour)
        max_entries:   Maximum cache size (default: 10,000 entries)
    
    Best for:
        - FAQ answers (same question, same answer every time)
        - Menu descriptions (changes at most daily)
        - Policy explanations (rarely change)
    
    NOT suitable for:
        - Personalized responses
        - Responses that depend on current state
        - Anything time-sensitive
    """
    
    def __init__(self, ttl_seconds: int = 3600, max_entries: int = 10_000):
        self._cache: dict[str, CacheEntry] = {}
        self._lock = Lock()
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self.total_requests = 0
        self.cache_hits = 0
    
    def _make_key(self, prompt: str, model: str, max_tokens: int) -> str:
        """Deterministic cache key from request parameters."""
        key_str = f"{model}:{max_tokens}:{prompt}"
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def get(self, prompt: str, model: str, max_tokens: int) -> Optional[str]:
        """Get cached response if available and not expired."""
        self.total_requests += 1
        key = self._make_key(prompt, model, max_tokens)
        
        with self._lock:
            entry = self._cache.get(key)
            if entry and (time.time() - entry.created_at) < self.ttl:
                entry.hits += 1
                self.cache_hits += 1
                return entry.response
            elif entry:
                del self._cache[key]  # Expired
        
        return None
    
    def set(self, prompt: str, model: str, max_tokens: int, response: str):
        """Cache a response."""
        key = self._make_key(prompt, model, max_tokens)
        
        with self._lock:
            # Evict oldest entry if at capacity
            if len(self._cache) >= self.max_entries:
                oldest_key = min(self._cache, key=lambda k: self._cache[k].created_at)
                del self._cache[oldest_key]
            
            self._cache[key] = CacheEntry(response=response, created_at=time.time())
    
    @property
    def hit_rate(self) -> float:
        return self.cache_hits / max(self.total_requests, 1)
    
    def stats(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "hit_rate_pct": round(self.hit_rate * 100, 1),
            "entries": len(self._cache),
            "capacity": self.max_entries,
        }

# Global cache — use one per application
response_cache = ResponseCache(ttl_seconds=1800, max_entries=5000)

def cached_claude_call(prompt: str, model: str = "claude-sonnet-4-6", max_tokens: int = 512) -> str:
    """
    Call Claude with application-layer caching.
    
    Cache hit: returns immediately (0ms API latency)
    Cache miss: calls Claude API and caches the result
    """
    # Check cache first
    cached = response_cache.get(prompt, model, max_tokens)
    if cached:
        return cached
    
    # Cache miss — call Claude
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    result = response.content[0].text
    
    # Cache the response
    response_cache.set(prompt, model, max_tokens, result)
    return result
```

### 6.2 Redis Cache (Production)

```python
import redis
import json
import hashlib

class RedisResponseCache:
    """
    Production response cache using Redis.
    
    Setup:
        pip install redis
        # Azure Cache for Redis: redis://your-cache.redis.cache.windows.net:6380
    
    Args:
        redis_url:   Redis connection URL
        ttl_seconds: Cache TTL (default: 3600)
        key_prefix:  Namespace prefix (default: "claude:")
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        ttl_seconds: int = 3600,
        key_prefix: str = "claude:",
    ):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.ttl = ttl_seconds
        self.prefix = key_prefix
    
    def _key(self, prompt: str, model: str, max_tokens: int) -> str:
        digest = hashlib.sha256(f"{model}:{max_tokens}:{prompt}".encode()).hexdigest()
        return f"{self.prefix}{digest}"
    
    def get(self, prompt: str, model: str, max_tokens: int) -> Optional[str]:
        value = self.redis.get(self._key(prompt, model, max_tokens))
        if value:
            data = json.loads(value)
            return data["response"]
        return None
    
    def set(self, prompt: str, model: str, max_tokens: int, response: str):
        key = self._key(prompt, model, max_tokens)
        value = json.dumps({"response": response, "model": model})
        self.redis.setex(key, self.ttl, value)
    
    def invalidate_pattern(self, prefix: str):
        """Invalidate all keys matching a pattern (e.g., on menu update)."""
        keys = self.redis.keys(f"{self.prefix}{prefix}*")
        if keys:
            self.redis.delete(*keys)
```

---

## 7. Tool Execution Optimization

Tools are the biggest latency contributor in agent pipelines. Minimize and parallelize them.

### 7.1 Parallel Tool Execution

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

def execute_tools_parallel(
    tool_calls: list,
    tool_executors: dict[str, Callable],
    timeout_per_tool: float = 30.0,
) -> list[dict]:
    """
    Execute all tool calls in the same response turn concurrently.
    
    This is safe when tool calls are independent (same-turn tool_use blocks
    from Claude are always independent — Claude can't make tool B depend
    on tool A in the same response turn).
    
    Args:
        tool_calls:      List of tool_use blocks from Claude's response
        tool_executors:  Dict of {tool_name: callable}
        timeout_per_tool: Max seconds per tool (default: 30)
    
    Returns:
        List of tool_result dicts ready to send back to Claude
    
    Example timing:
        3 tools, each takes 2s sequential:  6s total
        3 tools, each takes 2s parallel:    2s total
    """
    results = []
    
    with ThreadPoolExecutor(max_workers=len(tool_calls)) as executor:
        future_to_call = {}
        
        for tool_call in tool_calls:
            name = tool_call.name
            tool_input = tool_call.input
            
            if name not in tool_executors:
                # Unknown tool — return error immediately
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "is_error": True,
                    "content": json.dumps({"error": f"Unknown tool: {name}"}),
                })
                continue
            
            executor_fn = tool_executors[name]
            future = executor.submit(executor_fn, **tool_input)
            future_to_call[future] = tool_call
        
        for future in as_completed(future_to_call, timeout=timeout_per_tool):
            tool_call = future_to_call[future]
            try:
                result = future.result()
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": json.dumps(result) if not isinstance(result, str) else result,
                })
            except Exception as e:
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "is_error": True,
                    "content": json.dumps({"error": str(e), "tool": tool_call.name}),
                })
    
    return results
```

### 7.2 Tool Result Compression

Large tool results bloat the context window, increasing all subsequent TTFT values.

```python
def compress_tool_result(
    result: dict | list | str,
    max_chars: int = 2000,
    key_fields: list[str] = None,
) -> str:
    """
    Compress a tool result to fit within token budget.
    
    Strategies:
    1. Select only key fields (key_fields parameter)
    2. Truncate arrays to top N items
    3. Truncate string values
    4. Remove redundant/verbose fields
    
    Args:
        result:      Raw tool result
        max_chars:   Maximum characters in output (default: 2000 ≈ 500 tokens)
        key_fields:  If provided, only include these fields
    
    Returns:
        JSON string of compressed result
    """
    if isinstance(result, str):
        return result[:max_chars]
    
    if isinstance(result, list):
        # Limit to top 5 items
        result = result[:5]
    
    if isinstance(result, dict):
        if key_fields:
            result = {k: result[k] for k in key_fields if k in result}
        
        # Truncate long string values
        result = {
            k: v[:500] if isinstance(v, str) and len(v) > 500 else v
            for k, v in result.items()
        }
    
    compressed = json.dumps(result)
    if len(compressed) > max_chars:
        return compressed[:max_chars] + "... [truncated]"
    return compressed

# Usage in agent loop:
def execute_and_compress_tool(name: str, tool_input: dict) -> str:
    raw_result = tool_executors[name](**tool_input)
    return compress_tool_result(
        raw_result,
        max_chars=2000,
        # Only include fields Claude actually needs
        key_fields=get_relevant_fields(name)
    )
```

### 7.3 Tool Call Caching

Cache deterministic tool results to avoid repeated slow lookups.

```python
from functools import lru_cache
import hashlib

# Cache database lookups that don't change within a session
@lru_cache(maxsize=256)
def get_wine_details_cached(wine_id: str) -> str:
    """
    Cache wine lookups — same wine_id always returns same result.
    
    LRU cache is per-process. For multi-process, use Redis.
    """
    result = db.query_wine(wine_id)
    return json.dumps(result)

# For session-scoped tool caching:
class SessionToolCache:
    """Cache tool results within a single conversation session."""
    
    def __init__(self, ttl_seconds: int = 300):
        self._cache: dict[str, tuple[float, str]] = {}
        self.ttl = ttl_seconds
    
    def get_or_call(self, tool_name: str, tool_input: dict, executor_fn: Callable) -> str:
        """Get cached result or execute tool and cache result."""
        cache_key = f"{tool_name}:{hashlib.md5(json.dumps(tool_input, sort_keys=True).encode()).hexdigest()}"
        
        now = time.time()
        if cache_key in self._cache:
            timestamp, result = self._cache[cache_key]
            if now - timestamp < self.ttl:
                return result  # Cache hit — no tool call needed!
        
        # Cache miss — execute tool
        result = str(executor_fn(**tool_input))
        self._cache[cache_key] = (now, result)
        return result
```

---

## 8. Connection and HTTP Optimization

### 8.1 Reuse HTTP Connections

```python
import anthropic
import httpx

# ❌ Creates new connection on every call (slow)
def bad_example():
    for _ in range(100):
        client = anthropic.Anthropic()  # New client = new HTTP connection pool
        client.messages.create(...)

# ✅ Reuse the connection pool across all calls
client = anthropic.Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    # httpx settings for connection pooling
    http_client=httpx.Client(
        limits=httpx.Limits(
            max_keepalive_connections=20,  # Keep 20 connections alive
            max_connections=40,             # Allow up to 40 simultaneous
            keepalive_expiry=30,           # Reuse for 30 seconds
        ),
        timeout=httpx.Timeout(
            connect=5.0,   # Connection timeout: 5s
            read=120.0,    # Read timeout: 2 minutes (for long responses)
            write=10.0,    # Write timeout: 10s
            pool=5.0,      # Pool connection timeout: 5s
        ),
    )
)
```

### 8.2 Geographic Proximity

```python
# Anthropic API endpoints (as of 2026)
# All regions use api.anthropic.com — no regional endpoints
# BUT: your Azure deployment region affects your own service → Anthropic RTT

# Best practice: deploy your service in a region geographically close
# to Anthropic's inference infrastructure (US East / US West)

# For Azure deployments in Europe (e.g., UK South):
# Expected additional RTT: +80-120ms vs US East
# Mitigation: Use async streaming so first token arrives despite higher RTT

DEPLOYMENT_REGIONS = {
    "us-east-1":    {"estimated_rtt_ms": 20,  "recommendation": "Optimal"},
    "us-west-2":    {"estimated_rtt_ms": 50,  "recommendation": "Good"},
    "eu-west-2":    {"estimated_rtt_ms": 100, "recommendation": "Acceptable with streaming"},
    "ap-southeast-1": {"estimated_rtt_ms": 150, "recommendation": "Use streaming + cache"},
}
```

---

## 9. Model Selection for Latency

```python
from enum import Enum

class LatencyTier(Enum):
    INTERACTIVE = "interactive"    # User is waiting, <1s target
    STANDARD    = "standard"       # User is waiting, <3s acceptable
    BACKGROUND  = "background"     # User not watching, <30s
    BATCH       = "batch"          # Async, hours acceptable

# Model latency profiles (approximate, 2026):
MODEL_PROFILES = {
    "claude-haiku-4-5-20251001": {
        "ttft_typical_ms": 400,
        "tokens_per_sec":  120,
        "cost_per_1k_tokens": 0.000375,
        "quality": "Good for simple tasks",
    },
    "claude-sonnet-4-6": {
        "ttft_typical_ms": 800,
        "tokens_per_sec":  90,
        "cost_per_1k_tokens": 0.018,
        "quality": "Excellent for most tasks",
    },
    "claude-opus-4-6": {
        "ttft_typical_ms": 1500,
        "tokens_per_sec":  60,
        "cost_per_1k_tokens": 0.090,
        "quality": "Best for complex reasoning",
    },
}

def select_model_for_task(
    task_type: str,
    latency_tier: LatencyTier,
    quality_required: str = "standard",
) -> str:
    """
    Select model balancing latency and quality requirements.
    
    Args:
        task_type:       What kind of task (classification, generation, analysis)
        latency_tier:    How fast the response needs to be
        quality_required: "basic", "standard", or "premium"
    
    Returns:
        Model API string
    
    Examples:
        >>> select_model_for_task("classify_intent", LatencyTier.INTERACTIVE, "basic")
        "claude-haiku-4-5-20251001"
        
        >>> select_model_for_task("wine_recommendation", LatencyTier.STANDARD, "premium")
        "claude-sonnet-4-6"
        
        >>> select_model_for_task("strategy_report", LatencyTier.BATCH, "premium")
        "claude-opus-4-6"
    """
    # Interactive path: always prioritize speed
    if latency_tier == LatencyTier.INTERACTIVE:
        return "claude-haiku-4-5-20251001"
    
    # Premium quality required
    if quality_required == "premium" and latency_tier == LatencyTier.BATCH:
        return "claude-opus-4-6"
    
    # Default: Sonnet for balanced performance
    return "claude-sonnet-4-6"
```

---

## 10. Performance Monitoring and Alerting

### 10.1 Performance Targets

| Metric | Target (P50) | Target (P95) | Alert Threshold |
|--------|-------------|-------------|-----------------|
| TTFT — Haiku | < 500ms | < 1,200ms | > 2,000ms |
| TTFT — Sonnet | < 900ms | < 2,000ms | > 4,000ms |
| TTFT — Opus | < 1,800ms | < 4,000ms | > 8,000ms |
| Total response time (simple Q&A, 200 tokens) | < 2.5s | < 5s | > 10s |
| Total response time (detailed answer, 800 tokens) | < 10s | < 20s | > 40s |
| Agent loop (3 tool calls) | < 15s | < 30s | > 60s |
| Throughput (requests/min) | Monitor baseline | — | 20% drop |
| Cache hit rate | > 40% | — | < 10% |
| Error rate | < 0.5% | — | > 2% |

### 10.2 Application Insights Integration

```python
from applicationinsights import TelemetryClient

tc = TelemetryClient(os.environ.get("APPINSIGHTS_INSTRUMENTATIONKEY", ""))

class PerformanceMonitor:
    """
    Record Claude API performance metrics to Application Insights.
    
    Metrics tracked:
        claude.ttft_ms         — Time to first token
        claude.total_latency_ms — Full response time
        claude.output_tokens    — Tokens generated
        claude.cache_hit_rate   — Cache effectiveness
    """
    
    def record_call(
        self,
        model: str,
        prompt_tokens: int,
        output_tokens: int,
        ttft_ms: float,
        total_ms: float,
        cache_hit: bool,
        task_type: str,
    ):
        properties = {
            "model": model,
            "task_type": task_type,
            "cache_hit": str(cache_hit),
        }
        measurements = {
            "prompt_tokens": prompt_tokens,
            "output_tokens": output_tokens,
            "ttft_ms": ttft_ms,
            "total_latency_ms": total_ms,
            "tokens_per_second": output_tokens / max(total_ms / 1000, 0.001),
        }
        
        tc.track_event("claude_api_call", properties=properties, measurements=measurements)
        tc.track_metric("claude.ttft_ms", ttft_ms, properties={"model": model})
        tc.track_metric("claude.total_latency_ms", total_ms, properties={"model": model})
        
        # Alert on slow responses
        if ttft_ms > 4000:
            tc.track_event("claude_slow_ttft", {"ttft_ms": str(ttft_ms), "model": model})
        
        tc.flush()

monitor = PerformanceMonitor()
```

### 10.3 KQL Dashboard Queries (Azure Log Analytics)

```kusto
// P50/P95/P99 TTFT by model (last 24 hours)
customEvents
| where name == "claude_api_call"
| where timestamp > ago(24h)
| extend model = tostring(customDimensions.model)
| extend ttft_ms = todouble(customMeasurements.ttft_ms)
| summarize
    p50_ttft = percentile(ttft_ms, 50),
    p95_ttft = percentile(ttft_ms, 95),
    p99_ttft = percentile(ttft_ms, 99),
    request_count = count()
  by model, bin(timestamp, 1h)
| order by timestamp desc

// Cache effectiveness over time
customEvents
| where name == "claude_api_call"
| where timestamp > ago(7d)
| extend cache_hit = tobool(customDimensions.cache_hit)
| summarize
    total = count(),
    hits = countif(cache_hit == true)
  by bin(timestamp, 1h)
| extend hit_rate_pct = hits * 100.0 / total
| project timestamp, hit_rate_pct, total

// Slow response alert
customEvents
| where name == "claude_slow_ttft"
| where timestamp > ago(1h)
| count
// Alert if count > 10 in 1 hour
```

---

## 11. Junior Walkthrough — First Performance Audit

**Scenario**: "Our chat widget takes 4+ seconds to respond. How do I fix it?"

**Step 1: Measure first — don't guess**

```python
# Add timing to your existing call
import time

start = time.perf_counter()
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": user_question}],
)
total_ms = (time.perf_counter() - start) * 1000

print(f"Total: {total_ms:.0f}ms")
print(f"Input tokens: {response.usage.input_tokens}")
print(f"Output tokens: {response.usage.output_tokens}")
```

**Step 2: Enable streaming** — user sees first word in <1s regardless of total time

```python
# Before: wait 4s then show full response
response = client.messages.create(...)  # ← 4s wait
show_response(response.content[0].text)

# After: show tokens as they arrive
with client.messages.stream(...) as stream:
    for text in stream.text_stream:
        append_to_ui(text)  # ← User sees first word in ~0.5s
```

**Step 3: Check your prompt length** — are you accidentally sending huge prompts?

```python
count = client.messages.count_tokens(
    model="claude-sonnet-4-6",
    messages=your_messages,
)
print(f"You're sending {count.input_tokens} tokens per request")
# If > 5,000: you probably have unnecessary context — trim it
# If > 10,000: definitely optimize with RAG or summarization
```

**Step 4: Enable prompt caching** if you have a large stable system prompt

```python
# If your system prompt is > 1,024 tokens, cache it:
system = [{"type": "text", "text": your_system_prompt, "cache_control": {"type": "ephemeral"}}]
```

**Step 5: Consider Haiku for interactive paths**

```python
# If your chat widget doesn't need complex reasoning:
model = "claude-haiku-4-5-20251001"  # 3× faster TTFT, 12× cheaper
```

---

## 12. Senior Patterns — High-Traffic Production

### Cascade Architecture for High-Traffic Endpoints

```python
async def fast_classify_then_route(user_message: str) -> str:
    """
    Two-phase architecture for high-traffic production:
    1. Haiku (fast, cheap) classifies intent in ~400ms
    2. Route to appropriate specialist (Sonnet/Opus) based on classification
    
    Result: Interactive feel for routing, quality for answers.
    """
    # Phase 1: Fast classification (Haiku, ~400ms TTFT)
    classification = await client_async.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=20,
        messages=[{
            "role": "user",
            "content": f"Classify this restaurant query into ONE of: wine/menu/booking/complaint/other\nQuery: {user_message}\nOutput the category only."
        }]
    )
    intent = classification.content[0].text.strip().lower()
    
    # Phase 2: Specialist handler
    specialist_configs = {
        "wine":     {"model": "claude-sonnet-4-6", "max_tokens": 400, "system": SOMMELIER_PROMPT},
        "menu":     {"model": "claude-haiku-4-5-20251001", "max_tokens": 200, "system": MENU_PROMPT},
        "booking":  {"model": "claude-haiku-4-5-20251001", "max_tokens": 150, "system": BOOKING_PROMPT},
        "complaint":{"model": "claude-sonnet-4-6", "max_tokens": 500, "system": HOSPITALITY_PROMPT},
        "other":    {"model": "claude-haiku-4-5-20251001", "max_tokens": 200, "system": GENERAL_PROMPT},
    }
    
    config = specialist_configs.get(intent, specialist_configs["other"])
    
    response = await client_async.messages.create(
        messages=[{"role": "user", "content": user_message}],
        **config
    )
    return response.content[0].text

# Real-world improvement:
# Before: All queries → Sonnet, ~900ms TTFT, $0.018/call
# After:  70% queries → Haiku, ~400ms TTFT, $0.000375/call
#         30% queries → Sonnet, ~900ms TTFT, $0.018/call
# Blended: ~540ms TTFT, ~$0.0054/call (3× cheaper, 40% faster)
```

### Connection Warmup (Reduce Cold Start Latency)

```python
import asyncio

async def warm_connections():
    """
    Send a lightweight request at startup to warm HTTP connections
    and ensure the API client is ready before traffic arrives.
    
    Call this in your FastAPI startup event.
    """
    try:
        await client_async.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1,
            messages=[{"role": "user", "content": "ping"}],
        )
        print("Claude connection warmed successfully")
    except Exception as e:
        print(f"Warning: Could not warm Claude connection: {e}")

# FastAPI startup
@app.on_event("startup")
async def startup():
    await warm_connections()
    # Also pre-warm prompt cache
    await warm_prompt_cache()
```

---

## 13. Tips, Tricks, and Gotchas

### Tips

1. **Stream everything user-facing** — even if total time doesn't improve, UX improves dramatically
2. **Haiku for routing** — any binary or N-way classification where Haiku accuracy ≥ 95% should use Haiku
3. **Cache hit rate is a leading indicator** — if < 10%, your prompts are too variable; normalize before hashing
4. **pre-allocate asyncio tasks** — `asyncio.gather(*[task() for item in items])` beats sequential loops 10-50×
5. **Reuse the client** — creating a new `anthropic.Anthropic()` per request adds 10-50ms connection overhead

### Tricks

6. **Prefill to skip preamble** — `"assistant": "{"` forces JSON output without "Here is the JSON:" preamble, saving 20-50 tokens
7. **max_tokens discipline** — setting `max_tokens=10` for classification prevents runaway output and speeds up call by 2-5×
8. **compress_tool_result before returning** — if a search tool returns 50 results, return only top 5 with truncated descriptions; this prevents context bloat in subsequent turns
9. **Deduplicate FAQ prompts** — hash the question, strip stopwords, lowercase, then look up cache before calling API

### Gotchas

10. **Don't cache personalized responses** — caching by prompt hash will return wrong user's data if prompt includes user-specific info
11. **`flush=True` is mandatory for streaming print** — without it, Python buffers stdout and streaming looks broken
12. **SSE requires "Cache-Control: no-cache"** — browsers aggressively cache SSE streams otherwise; add the header
13. **asyncio.gather errors silently** — always pass `return_exceptions=True` or individual exceptions will surface as None results
14. **Cache TTL must match data freshness** — caching menu descriptions with TTL=86400 (1 day) is fine; caching availability queries with TTL=3600 is not

---

## 14. Quick Reference Cheatsheet

```python
# ═══════════════════════════════════════════════════════════════
# PERFORMANCE TUNING QUICK REFERENCE
# ═══════════════════════════════════════════════════════════════

# 1. LATENCY DECOMPOSITION
# Total = Network RTT + TTFT + Generation + Tool time
# TTFT grows ~5ms per 1,000 input tokens (uncached)
# TTFT drops ~40% with prompt cache hits

# 2. FASTEST CALL POSSIBLE
response = client.messages.create(
    model="claude-haiku-4-5-20251001",   # Fastest model
    max_tokens=10,                        # Limit output
    messages=[{"role": "user", "content": "Classify: wine/menu/other — Query: " + q}],
)
# Expected: ~400ms TTFT, ~600ms total

# 3. STREAMING SETUP
with client.messages.stream(model=..., max_tokens=..., messages=[...]) as s:
    for text in s.text_stream:
        print(text, end="", flush=True)   # flush=True is critical
    final = s.get_final_message()

# 4. ASYNC PARALLEL
results = await asyncio.gather(*[call_claude(item) for item in items])

# 5. RATE LIMITED CONCURRENCY
semaphore = asyncio.Semaphore(10)  # Max 10 concurrent
async with semaphore:
    result = await client_async.messages.create(...)

# 6. PROMPT CACHE
system = [{"type": "text", "text": BIG_STABLE_PROMPT, "cache_control": {"type": "ephemeral"}}]

# 7. RESPONSE CACHE KEY
key = hashlib.sha256(f"{model}:{max_tokens}:{prompt}".encode()).hexdigest()

# 8. PERFORMANCE TARGETS
# Haiku TTFT:  < 500ms (P50), < 1,200ms (P95)
# Sonnet TTFT: < 900ms (P50), < 2,000ms (P95)
# Agent loop:  < 15s   (P50), < 30s    (P95)
# Cache rate:  > 40% (alert if < 10%)

# 9. MODEL SELECTION
# Interactive (<1s):    Haiku
# Standard (<3s):       Sonnet (cached system prompt)
# Quality (batch):      Opus
# Default:              Sonnet

# 10. TOOL EXECUTION
# Always parallel: ThreadPoolExecutor(max_workers=len(tool_calls))
# Always compress: return result[:2000] not full DB response
# Always timeout:  future.result(timeout=30)
```
