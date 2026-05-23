# error-handling.md — Error Handling, Retries, and Fallback Patterns

> **Purpose**: Production-grade error handling for Claude API integrations. Covers every error type, retry strategies, circuit breakers, context overflow, graceful degradation, timeout management, and full observability.
> **Who This Is For**: Junior developers learning API error handling; senior engineers building fault-tolerant production systems.
> **Owner**: jose@hybridgenai.com

---

## Navigation

1. [Claude API Error Taxonomy](#1-claude-api-error-taxonomy)
2. [Retry with Exponential Backoff and Jitter](#2-retry-with-exponential-backoff-and-jitter)
3. [Context Length Overflow Handling](#3-context-length-overflow-handling)
4. [Circuit Breaker Pattern](#4-circuit-breaker-pattern)
5. [Graceful Degradation (3-Tier Fallback)](#5-graceful-degradation-3-tier-fallback)
6. [Timeout Management](#6-timeout-management)
7. [Tool Error Handling in Agents](#7-tool-error-handling-in-agents)
8. [Streaming Error Handling](#8-streaming-error-handling)
9. [Error Monitoring and Observability](#9-error-monitoring-and-observability)
10. [Junior Walkthrough — Handle Your First Rate Limit](#10-junior-walkthrough--handle-your-first-rate-limit)
11. [Senior Patterns — Full Production Error Infrastructure](#11-senior-patterns--full-production-error-infrastructure)
12. [Tips, Tricks, and Gotchas](#12-tips-tricks-and-gotchas)
13. [Quick Reference Cheatsheet](#13-quick-reference-cheatsheet)

---

## 1. Claude API Error Taxonomy

Every error has a correct response strategy. The cardinal rule: **only retry transient errors**.

```
┌──────────┬────────────────────────┬──────────────────────────────┬───────────────────────┐
│ HTTP     │ Error Type             │ Common Causes                │ Correct Action        │
├──────────┼────────────────────────┼──────────────────────────────┼───────────────────────┤
│ 400      │ invalid_request_error  │ Bad JSON, invalid param,     │ FIX the request.      │
│          │                        │ prompt too long, bad model   │ NEVER retry.          │
├──────────┼────────────────────────┼──────────────────────────────┼───────────────────────┤
│ 401      │ authentication_error   │ Invalid/missing API key,     │ Check credentials.    │
│          │                        │ expired key                  │ NEVER retry.          │
├──────────┼────────────────────────┼──────────────────────────────┼───────────────────────┤
│ 403      │ permission_error       │ Model not available for your │ Check your account    │
│          │                        │ tier, region restriction     │ permissions. No retry.│
├──────────┼────────────────────────┼──────────────────────────────┼───────────────────────┤
│ 404      │ not_found_error        │ Invalid model string,        │ Fix model string.     │
│          │                        │ resource doesn't exist       │ NEVER retry.          │
├──────────┼────────────────────────┼──────────────────────────────┼───────────────────────┤
│ 413      │ request_too_large      │ Prompt exceeds 200K tokens   │ Trim prompt. No retry.│
├──────────┼────────────────────────┼──────────────────────────────┼───────────────────────┤
│ 429      │ rate_limit_error       │ Exceeded RPM or TPM quota    │ RETRY with backoff.   │
│          │                        │                              │ Respect Retry-After.  │
├──────────┼────────────────────────┼──────────────────────────────┼───────────────────────┤
│ 500      │ api_error              │ Anthropic internal error     │ RETRY with backoff.   │
├──────────┼────────────────────────┼──────────────────────────────┼───────────────────────┤
│ 529      │ overloaded_error       │ Service overloaded,          │ RETRY with longer     │
│          │                        │ high demand                  │ backoff (start at 5s).│
├──────────┼────────────────────────┼──────────────────────────────┼───────────────────────┤
│ N/A      │ APIConnectionError     │ Network failure, DNS issue   │ RETRY immediately     │
│          │                        │                              │ (1-2 attempts).       │
├──────────┼────────────────────────┼──────────────────────────────┼───────────────────────┤
│ N/A      │ APITimeoutError        │ Request timeout              │ RETRY once; then      │
│          │                        │                              │ use fallback.         │
└──────────┴────────────────────────┴──────────────────────────────┴───────────────────────┘

RETRYABLE:     429, 500, 529, APIConnectionError, APITimeoutError
NOT RETRYABLE: 400, 401, 403, 404, 413
```

### Error Imports and Setup

```python
import time
import random
import asyncio
import anthropic
from anthropic import (
    RateLimitError,       # 429 — rate limit exceeded
    APIStatusError,       # General HTTP error with status_code attribute
    APIConnectionError,   # Network-level failure
    APITimeoutError,      # Request timed out
    BadRequestError,      # 400 — invalid request parameters
    AuthenticationError,  # 401 — bad API key
    PermissionDeniedError,# 403 — insufficient permissions
    NotFoundError,        # 404 — model or resource not found
)
import os

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
client_async = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# Status codes that indicate transient errors (safe to retry)
RETRYABLE_STATUS_CODES = {429, 500, 529}
```

---

## 2. Retry with Exponential Backoff and Jitter

### 2.1 Synchronous Retry

```python
def call_claude_with_retry(
    max_retries: int = 5,
    base_delay_seconds: float = 1.0,
    max_delay_seconds: float = 60.0,
    jitter: bool = True,
    **kwargs,
) -> anthropic.types.Message:
    """
    Call Claude's messages.create with automatic retry for transient errors.
    
    Retry strategy: Exponential backoff with optional jitter.
    - Attempt 1: Immediate
    - Attempt 2: ~1s delay
    - Attempt 3: ~2s delay
    - Attempt 4: ~4s delay
    - Attempt 5: ~8s delay (capped at max_delay_seconds)
    
    Jitter: Adds random offset to prevent "thundering herd" — all clients
    retrying at the exact same time after a rate limit event.
    
    Args:
        max_retries:         Maximum attempts (default: 5)
        base_delay_seconds:  Initial backoff delay (default: 1.0s)
        max_delay_seconds:   Maximum backoff cap (default: 60s)
        jitter:              Add random ±20% jitter to delays (default: True)
        **kwargs:            Passed directly to client.messages.create()
    
    Returns:
        anthropic.types.Message on success
    
    Raises:
        Last exception if all retries exhausted.
    
    Usage:
        response = call_claude_with_retry(
            max_retries=5,
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": "Hello"}],
        )
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return client.messages.create(**kwargs)
        
        except RateLimitError as e:
            last_exception = e
            if attempt == max_retries - 1:
                raise
            
            # Respect the Retry-After header if present
            retry_after_header = getattr(e.response, 'headers', {}).get('retry-after', None)
            if retry_after_header:
                wait = float(retry_after_header)
            else:
                wait = base_delay_seconds * (2 ** attempt)
            
            if jitter:
                wait += random.uniform(0, wait * 0.2)  # ±20% jitter
            
            wait = min(wait, max_delay_seconds)
            print(f"[Retry {attempt + 1}/{max_retries}] Rate limited. Waiting {wait:.1f}s...")
            time.sleep(wait)
        
        except APIStatusError as e:
            last_exception = e
            if e.status_code not in RETRYABLE_STATUS_CODES:
                raise  # Don't retry 400, 401, 403, 404, 413
            
            if attempt == max_retries - 1:
                raise
            
            # Longer initial delay for 529 (overloaded)
            base = base_delay_seconds * 5 if e.status_code == 529 else base_delay_seconds
            wait = min(base * (2 ** attempt) + (random.uniform(0, 1) if jitter else 0), max_delay_seconds)
            print(f"[Retry {attempt + 1}/{max_retries}] API error {e.status_code}. Waiting {wait:.1f}s...")
            time.sleep(wait)
        
        except APIConnectionError as e:
            last_exception = e
            if attempt == max_retries - 1:
                raise
            # Brief pause for connection issues (often transient)
            wait = min(base_delay_seconds * (2 ** attempt), 10.0)
            time.sleep(wait)
        
        except APITimeoutError as e:
            last_exception = e
            if attempt >= 2:  # Only retry timeouts twice
                raise
            time.sleep(base_delay_seconds)
    
    raise last_exception
```

### 2.2 Async Retry

```python
async def call_claude_async_with_retry(
    max_retries: int = 5,
    base_delay_seconds: float = 1.0,
    max_delay_seconds: float = 60.0,
    **kwargs,
) -> anthropic.types.Message:
    """
    Async version of call_claude_with_retry.
    
    Use in FastAPI handlers, async agents, and any asyncio context.
    Same retry logic as synchronous version but uses asyncio.sleep.
    
    Usage:
        response = await call_claude_async_with_retry(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": user_question}],
        )
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await client_async.messages.create(**kwargs)
        
        except RateLimitError as e:
            last_exception = e
            if attempt == max_retries - 1:
                raise
            
            retry_after = float(getattr(e.response, 'headers', {}).get('retry-after', base_delay_seconds))
            wait = min(retry_after * (2 ** attempt) + random.uniform(0, 1), max_delay_seconds)
            await asyncio.sleep(wait)
        
        except APIStatusError as e:
            last_exception = e
            if e.status_code not in RETRYABLE_STATUS_CODES or attempt == max_retries - 1:
                raise
            wait = min(base_delay_seconds * (2 ** attempt) + random.uniform(0, 1), max_delay_seconds)
            await asyncio.sleep(wait)
        
        except (APIConnectionError, APITimeoutError) as e:
            last_exception = e
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(min(base_delay_seconds * (2 ** attempt), 10.0))
    
    raise last_exception
```

---

## 3. Context Length Overflow Handling

### 3.1 Detect and Recover from 400 Errors

```python
def handle_context_overflow(
    messages: list[dict],
    system: str = "",
    model: str = "claude-sonnet-4-6",
    max_retries: int = 4,
    trim_fraction: float = 0.25,
) -> str:
    """
    Handle context-too-long errors by progressively trimming the message history.
    
    Trim strategy: Remove the oldest 25% of messages on each retry.
    
    Args:
        messages:      Conversation history
        system:        System prompt
        model:         Model to use
        max_retries:   Maximum trim-and-retry attempts (default: 4)
        trim_fraction: Fraction of messages to remove each try (default: 0.25)
    
    Returns:
        Claude's response text
    
    Raises:
        ValueError if context still too large after max_retries
        Any non-overflow error immediately (no retry)
    
    Example:
        # 30-turn conversation → 400 "prompt too long"
        # Trim 25% (8 messages) → retry → success
    """
    working_messages = list(messages)  # Don't mutate original
    
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                system=system,
                messages=working_messages,
            )
            return response.content[0].text
        
        except BadRequestError as e:
            error_str = str(e).lower()
            
            # Only handle context length errors
            if "too long" not in error_str and "token" not in error_str:
                raise  # Re-raise other 400s (don't try to fix them)
            
            if attempt == max_retries - 1:
                raise ValueError(
                    f"Cannot reduce context further after {max_retries} attempts. "
                    f"Current messages: {len(working_messages)}"
                )
            
            # Trim oldest messages
            n_to_remove = max(2, int(len(working_messages) * trim_fraction))
            # Ensure we remove pairs (user+assistant) to keep conversation valid
            if n_to_remove % 2 != 0:
                n_to_remove += 1
            
            working_messages = working_messages[n_to_remove:]
            
            # Ensure first message is user (API requirement)
            while working_messages and working_messages[0]["role"] != "user":
                working_messages = working_messages[1:]
            
            print(f"Context too long. Trimmed {n_to_remove} messages. {len(working_messages)} remain.")
```

### 3.2 Proactive Context Overflow Prevention

```python
def safe_send(
    messages: list[dict],
    system: str = "",
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 1024,
    safety_margin_pct: float = 0.15,
) -> anthropic.types.Message:
    """
    Check token count BEFORE sending and trim if needed.
    
    Prevents 400 errors by checking proactively.
    Cheaper than catching and retrying a failed request.
    
    Args:
        messages:          Conversation messages
        system:            System prompt
        model:             Claude model
        max_tokens:        Output token reservation
        safety_margin_pct: Reserve this % as safety buffer (default: 15%)
    
    Returns:
        API response
    """
    MODEL_LIMITS = {
        "claude-opus-4-6": 200_000,
        "claude-sonnet-4-6": 200_000,
        "claude-haiku-4-5-20251001": 200_000,
    }
    
    limit = MODEL_LIMITS.get(model, 200_000)
    usable = int(limit * (1 - safety_margin_pct)) - max_tokens
    
    # Proactive count
    working = list(messages)
    
    while len(working) > 2:
        count = client.messages.count_tokens(model=model, system=system, messages=working)
        
        if count.input_tokens <= usable:
            break
        
        # Trim 2 oldest messages
        working = working[2:]
        if working and working[0]["role"] != "user":
            working = working[1:]
    
    return client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=working,
    )
```

---

## 4. Circuit Breaker Pattern

Prevents cascading failures when the API is consistently failing.

```python
from enum import Enum
from threading import Lock
from dataclasses import dataclass, field
import time

class CircuitState(Enum):
    CLOSED   = "closed"    # Normal operation — requests pass through
    OPEN     = "open"      # Failing — block all requests immediately
    HALF_OPEN = "half_open" # Recovering — allow one test request

@dataclass
class CircuitBreaker:
    """
    Circuit breaker for Claude API calls.
    
    States:
        CLOSED:    Normal — all requests pass through
        OPEN:      Tripped — all requests blocked for reset_timeout seconds
        HALF_OPEN: Recovering — one test request allowed
    
    Args:
        failure_threshold: Consecutive failures to trip breaker (default: 5)
        reset_timeout:     Seconds to wait before allowing test request (default: 60)
        success_threshold: Successes in HALF_OPEN to close breaker (default: 2)
    
    Usage:
        breaker = CircuitBreaker(failure_threshold=5, reset_timeout=60)
        try:
            response = breaker.call(
                client.messages.create,
                model="claude-sonnet-4-6",
                messages=[...],
                max_tokens=512,
            )
        except CircuitBreakerOpenError:
            return static_fallback_response()
    
    Real-world scenario:
        Anthropic has an incident at 14:00.
        After 5 failures in a row → breaker opens.
        For the next 60 seconds: all Claude calls are blocked immediately.
        Your service keeps responding with static fallbacks.
        At 14:01: test request allowed → succeeds → breaker closes.
        Normal service resumes with no thundering herd.
    """
    
    failure_threshold: int = 5
    reset_timeout: float = 60.0
    success_threshold: int = 2
    
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _success_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)
    
    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time >= self.reset_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
            return self._state
    
    def call(self, fn: callable, *args, **kwargs):
        """
        Execute fn if circuit allows; raise CircuitBreakerOpenError if open.
        
        Args:
            fn:      The callable to execute (e.g., client.messages.create)
            *args:   Positional arguments for fn
            **kwargs: Keyword arguments for fn
        """
        current_state = self.state
        
        if current_state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit breaker OPEN. {self.reset_timeout}s cooldown. "
                f"Last failure: {int(time.time() - self._last_failure_time)}s ago."
            )
        
        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        
        except (RateLimitError, APIStatusError, APIConnectionError) as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    print("Circuit breaker CLOSED — API recovering")
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0  # Reset on success
    
    def _on_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN  # Test request failed — stay open
                print(f"Circuit breaker stays OPEN — test request failed")
            
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    print(f"Circuit breaker OPENED after {self._failure_count} failures")
    
    def status(self) -> dict:
        return {
            "state": self.state.value,
            "failure_count": self._failure_count,
            "seconds_until_reset": max(0, self.reset_timeout - (time.time() - self._last_failure_time))
            if self._state != CircuitState.CLOSED else 0,
        }

class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and blocking requests."""
    pass

# Global circuit breaker — shared across all Claude calls in the process
claude_circuit_breaker = CircuitBreaker(failure_threshold=5, reset_timeout=60)
```

---

## 5. Graceful Degradation (3-Tier Fallback)

```python
from typing import Optional
import re

class ResilientRestaurantAssistant:
    """
    3-tier fallback architecture for production resilience.
    
    Tier 1: Primary model (claude-sonnet-4-6) — best quality
    Tier 2: Fallback model (claude-haiku-4-5-20251001) — faster, cheaper
    Tier 3: Static responses — works even when API is completely down
    
    Failure scenarios handled:
    - Rate limits (429)
    - Service overloaded (529)
    - Internal errors (500)
    - Network failures
    - Circuit breaker open
    
    Usage:
        assistant = ResilientRestaurantAssistant()
        response = assistant.chat("Do you have vegan options?")
        # Returns answer from best available tier
    """
    
    PRIMARY_MODEL   = "claude-sonnet-4-6"
    FALLBACK_MODEL  = "claude-haiku-4-5-20251001"
    
    # Static fallbacks for complete API unavailability
    STATIC_RESPONSES = {
        "wine":    "Our sommelier will be happy to help you select the perfect wine. Please ask your server.",
        "menu":    "Our current menu is available from your server. We're happy to accommodate dietary requirements — please ask.",
        "booking": "For reservations, please call us at +44 20 7XXX XXXX or email reservations@lumiere.co.uk.",
        "allergy": "Please inform your server of any allergies or dietary requirements. Our kitchen takes all allergen queries seriously.",
        "default": "I'm temporarily unavailable. Our team is here to assist you — please speak with your server or host.",
    }
    
    def __init__(self, system_prompt: str = ""):
        self.system = system_prompt
        self.breaker = CircuitBreaker(failure_threshold=5, reset_timeout=60)
        self._tier_stats = {"tier1_used": 0, "tier2_used": 0, "tier3_used": 0}
    
    def chat(self, user_message: str, messages: list = None) -> dict:
        """
        Send a message with full fallback chain.
        
        Returns:
            {
                "response": str,          # The response text
                "tier": int,              # Which tier responded (1/2/3)
                "model": str | None,      # Model used (None for tier 3)
                "degraded": bool,         # True if not tier 1
            }
        """
        msgs = messages or [{"role": "user", "content": user_message}]
        
        # ── TIER 1: Primary model ──────────────────────────────────────
        try:
            response = self.breaker.call(
                call_claude_with_retry,
                model=self.PRIMARY_MODEL,
                max_tokens=600,
                system=self.system,
                messages=msgs,
                max_retries=3,
            )
            self._tier_stats["tier1_used"] += 1
            return {
                "response": response.content[0].text,
                "tier": 1,
                "model": self.PRIMARY_MODEL,
                "degraded": False,
            }
        
        except (CircuitBreakerOpenError, Exception) as e1:
            tier1_error = str(e1)
        
        # ── TIER 2: Fallback model ─────────────────────────────────────
        try:
            response = client.messages.create(
                model=self.FALLBACK_MODEL,
                max_tokens=400,  # Smaller output for speed
                system=self.system,
                messages=msgs,
            )
            self._tier_stats["tier2_used"] += 1
            return {
                "response": response.content[0].text,
                "tier": 2,
                "model": self.FALLBACK_MODEL,
                "degraded": True,
            }
        
        except Exception as e2:
            tier2_error = str(e2)
        
        # ── TIER 3: Static response ────────────────────────────────────
        category = self._classify_statically(user_message)
        static_response = self.STATIC_RESPONSES.get(category, self.STATIC_RESPONSES["default"])
        self._tier_stats["tier3_used"] += 1
        
        return {
            "response": static_response,
            "tier": 3,
            "model": None,
            "degraded": True,
        }
    
    def _classify_statically(self, message: str) -> str:
        """Classify intent without any API call — uses regex only."""
        m = message.lower()
        if re.search(r"\b(wine|bottle|red|white|sparkling|champagne)\b", m): return "wine"
        if re.search(r"\b(menu|dish|food|eat|starter|main|dessert)\b", m): return "menu"
        if re.search(r"\b(book|reservation|table|available)\b", m): return "booking"
        if re.search(r"\b(allerg|intoleran|vegan|gluten|nut|dairy)\b", m): return "allergy"
        return "default"
    
    def stats(self) -> dict:
        total = sum(self._tier_stats.values())
        return {
            **self._tier_stats,
            "total_requests": total,
            "tier1_rate": round(self._tier_stats["tier1_used"] / max(total, 1) * 100, 1),
            "degraded_rate": round((self._tier_stats["tier2_used"] + self._tier_stats["tier3_used"]) / max(total, 1) * 100, 1),
            "circuit_breaker": claude_circuit_breaker.status(),
        }
```

---

## 6. Timeout Management

Hanging requests are a silent killer of user experience and resource utilization.

```python
import asyncio
from contextlib import asynccontextmanager

# ── Timeout budget by path type ──────────────────────────────────────────
TIMEOUT_CONFIG = {
    "realtime_chat":    10.0,   # User is actively waiting — tight budget
    "rag_query":        20.0,   # Search + generate — slightly more slack
    "agent_step":       30.0,   # Single agent loop step
    "agent_total":     120.0,   # Full agent run (multiple tool calls)
    "document_summary": 60.0,   # Processing a full document
    "batch_item":       45.0,   # Async batch processing
    "classification":    8.0,   # Should be very fast
}

async def call_with_timeout(
    coro,
    timeout_seconds: float,
    path: str = "unknown",
):
    """
    Execute a coroutine with a timeout.
    
    Args:
        coro:             Awaitable to execute
        timeout_seconds:  Maximum seconds to wait
        path:             Path name for error messages
    
    Raises:
        asyncio.TimeoutError if exceeded
    
    Usage:
        try:
            response = await call_with_timeout(
                client_async.messages.create(...),
                timeout_seconds=TIMEOUT_CONFIG["realtime_chat"],
                path="realtime_chat",
            )
        except asyncio.TimeoutError:
            return fallback_response
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise asyncio.TimeoutError(
            f"Claude API call timed out after {timeout_seconds}s on path '{path}'"
        )

# ── Streaming with absolute timeout ───────────────────────────────────────
async def stream_with_timeout(
    timeout_seconds: float = 30.0,
    **kwargs,
) -> str:
    """
    Stream a response with an absolute wall-clock timeout.
    
    Returns partial text if timeout occurs mid-stream.
    """
    collected = ""
    
    async def _stream():
        nonlocal collected
        async with client_async.messages.stream(**kwargs) as s:
            async for text in s.text_stream:
                collected += text
        return collected
    
    try:
        return await asyncio.wait_for(_stream(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        if collected:
            return collected + "\n[Response truncated due to timeout]"
        raise

# ── Layered timeouts for agent loops ──────────────────────────────────────
class AgentTimeoutManager:
    """
    Enforce both per-step and total timeouts in agent loops.
    
    Args:
        step_timeout:  Max seconds per agent step (default: 30s)
        total_timeout: Max seconds for entire agent run (default: 120s)
    
    Usage:
        tm = AgentTimeoutManager(step_timeout=30, total_timeout=120)
        tm.start_run()
        for step in range(MAX_STEPS):
            with tm.step_context():
                response = await tm.call(some_coroutine)
    """
    
    def __init__(self, step_timeout: float = 30.0, total_timeout: float = 120.0):
        self.step_timeout = step_timeout
        self.total_timeout = total_timeout
        self._run_start: Optional[float] = None
    
    def start_run(self):
        self._run_start = time.monotonic()
    
    @property
    def elapsed(self) -> float:
        return time.monotonic() - (self._run_start or time.monotonic())
    
    @property
    def total_remaining(self) -> float:
        return max(0, self.total_timeout - self.elapsed)
    
    def check_total_timeout(self):
        if self.elapsed > self.total_timeout:
            raise asyncio.TimeoutError(f"Agent total timeout exceeded ({self.total_timeout}s)")
    
    async def call(self, coro, step_name: str = ""):
        """Execute a coroutine respecting both step and total timeouts."""
        self.check_total_timeout()
        
        # Use the smaller of step timeout and remaining total time
        effective_timeout = min(self.step_timeout, self.total_remaining)
        
        try:
            return await asyncio.wait_for(coro, timeout=effective_timeout)
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError(
                f"Step '{step_name}' timed out after {effective_timeout:.1f}s "
                f"(total elapsed: {self.elapsed:.1f}s / {self.total_timeout}s)"
            )
```

---

## 7. Tool Error Handling in Agents

```python
def tool_result_success(tool_use_id: str, result: any) -> dict:
    """
    Create a successful tool_result message block.
    
    Args:
        tool_use_id: ID from the tool_use block (must match exactly)
        result:      The tool's result (will be JSON-serialized if not a string)
    
    Returns:
        tool_result message block ready to add to messages list
    """
    content = result if isinstance(result, str) else json.dumps(result)
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content,
    }

def tool_result_error(tool_use_id: str, error_message: str, error_type: str = "ToolError") -> dict:
    """
    Create an error tool_result message block.
    
    Claude handles tool errors gracefully — it will either:
    1. Try a different approach
    2. Report the error to the user
    3. Use its knowledge without the tool result
    
    IMPORTANT: Always return a tool_result for EVERY tool_use block,
    even if the tool failed. Leaving a tool_use block without a corresponding
    tool_result causes a 400 error on the next API call.
    
    Args:
        tool_use_id:   ID from the tool_use block
        error_message: Human-readable error description
        error_type:    Error category for Claude's understanding
    
    Returns:
        tool_result message block with is_error=True
    
    Usage:
        try:
            result = tool_executors[tool_name](**tool_input)
            return tool_result_success(tool_id, result)
        except Exception as e:
            return tool_result_error(tool_id, str(e), type(e).__name__)
    """
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "is_error": True,
        "content": json.dumps({
            "error": error_message,
            "error_type": error_type,
            "suggestion": "Try a different approach or inform the user.",
        }),
    }

class ToolFailureBudget:
    """
    Track and enforce a failure budget per tool in an agent session.
    
    Prevents agents from getting stuck in loops retrying broken tools.
    After max_failures failures for a tool, that tool is disabled
    for the rest of the session.
    
    Args:
        max_failures_per_tool: Maximum allowed failures per tool (default: 3)
    
    Usage:
        budget = ToolFailureBudget(max_failures_per_tool=3)
        
        try:
            result = execute_tool(tool_name, tool_input)
        except Exception as e:
            budget.record_failure(tool_name, str(e))
            if budget.is_disabled(tool_name):
                # Remove from tools list for next Claude call
                tools = [t for t in tools if t["name"] != tool_name]
            return tool_result_error(tool_id, str(e))
    """
    
    def __init__(self, max_failures_per_tool: int = 3):
        self.max_failures = max_failures_per_tool
        self._failures: dict[str, list[str]] = {}  # {tool_name: [error1, error2, ...]}
    
    def record_failure(self, tool_name: str, error: str):
        self._failures.setdefault(tool_name, []).append(error)
    
    def failure_count(self, tool_name: str) -> int:
        return len(self._failures.get(tool_name, []))
    
    def is_disabled(self, tool_name: str) -> bool:
        return self.failure_count(tool_name) >= self.max_failures
    
    def disabled_tools(self) -> list[str]:
        return [name for name in self._failures if self.is_disabled(name)]
    
    def filter_tools(self, tools: list[dict]) -> list[dict]:
        """Remove disabled tools from tools list."""
        disabled = set(self.disabled_tools())
        return [t for t in tools if t["name"] not in disabled]
    
    def summary(self) -> dict:
        return {name: {"failures": len(errors), "disabled": self.is_disabled(name)}
                for name, errors in self._failures.items()}
```

---

## 8. Streaming Error Handling

```python
async def robust_stream_handler(
    messages: list,
    system: str = "",
    on_token: callable = None,    # Called with each text token
    on_error: callable = None,    # Called with error string
    on_complete: callable = None, # Called with (full_text, usage)
    timeout: float = 60.0,
) -> str:
    """
    Stream handler with full error recovery.
    
    Args:
        messages:    Conversation messages
        system:      System prompt
        on_token:    Callback for each streamed token: (text: str) -> None
        on_error:    Callback for errors: (error: str) -> None
        on_complete: Callback on completion: (text: str, usage: dict) -> None
        timeout:     Total streaming timeout
    
    Returns:
        Accumulated response text (may be partial if error occurred)
    """
    full_text = ""
    
    try:
        async with asyncio.timeout(timeout):
            async with client_async.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=system,
                messages=messages,
            ) as stream:
                try:
                    async for text in stream.text_stream:
                        full_text += text
                        if on_token:
                            on_token(text)
                    
                    final = await stream.get_final_message()
                    
                    if on_complete:
                        on_complete(full_text, {
                            "input_tokens": final.usage.input_tokens,
                            "output_tokens": final.usage.output_tokens,
                        })
                
                except Exception as stream_error:
                    # Mid-stream error — return what we have
                    err_msg = f"Stream interrupted: {str(stream_error)}"
                    if on_error:
                        on_error(err_msg)
                    if full_text:
                        return full_text + "\n[Stream interrupted]"
                    raise
    
    except asyncio.TimeoutError:
        err_msg = f"Stream timed out after {timeout}s"
        if on_error:
            on_error(err_msg)
        if full_text:
            return full_text + "\n[Timeout — partial response]"
        raise
    
    except RateLimitError as e:
        if on_error:
            on_error("Rate limit reached. Please try again in a moment.")
        raise
    
    except BadRequestError as e:
        if on_error:
            on_error("Invalid request. Please rephrase your message.")
        raise
    
    return full_text
```

---

## 9. Error Monitoring and Observability

```python
import logging
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger("claude.errors")

@dataclass
class ErrorMetrics:
    """
    Track error rates by type and model for operational monitoring.
    
    Exposes metrics for:
    - Per-error-type counts
    - Per-model error rates
    - Rate limit frequency
    - Success/failure ratio
    """
    _counts: dict = field(default_factory=lambda: defaultdict(int), init=False)
    _total_requests: int = field(default=0, init=False)
    _success_count: int = field(default=0, init=False)
    
    def record_success(self):
        self._total_requests += 1
        self._success_count += 1
    
    def record_error(self, error: Exception, model: str = "", context: dict = None):
        self._total_requests += 1
        error_type = type(error).__name__
        
        self._counts[f"total.{error_type}"] += 1
        if model:
            self._counts[f"model.{model}.{error_type}"] += 1
        if isinstance(error, APIStatusError):
            self._counts[f"http.{error.status_code}"] += 1
        
        # Structured logging for Log Analytics
        log_data = {
            "error_type": error_type,
            "model": model,
            "message": str(error)[:300],
            "timestamp": datetime.utcnow().isoformat(),
            "context": context or {},
        }
        
        if isinstance(error, (RateLimitError,)):
            logger.warning(f"Claude rate limit: {log_data}")
        elif isinstance(error, (APIStatusError,)) and error.status_code >= 500:
            logger.error(f"Claude API error: {log_data}")
        else:
            logger.error(f"Claude error: {log_data}")
    
    @property
    def error_rate(self) -> float:
        return 1.0 - (self._success_count / max(self._total_requests, 1))
    
    def report(self) -> dict:
        return {
            "total_requests": self._total_requests,
            "success_count": self._success_count,
            "error_rate_pct": round(self.error_rate * 100, 2),
            "error_counts": dict(self._counts),
        }

# ── Application Insights Integration ─────────────────────────────────────
from applicationinsights import TelemetryClient

class ClaudeErrorMonitor:
    """
    Send error events and metrics to Application Insights.
    
    KQL Queries for dashboards:
    
    // Error rate over time
    customEvents
    | where name == "claude_api_error"
    | summarize errors = count() by bin(timestamp, 5m), error_type = tostring(customDimensions.error_type)
    
    // Rate limit frequency (indicator of needing quota increase)
    customEvents
    | where name == "claude_api_error"
    | where customDimensions.error_type == "RateLimitError"
    | summarize count() by bin(timestamp, 1h)
    """
    
    def __init__(self, instrumentation_key: str):
        self.tc = TelemetryClient(instrumentation_key)
        self.metrics = ErrorMetrics()
    
    def on_success(self, model: str, input_tokens: int, output_tokens: int):
        self.metrics.record_success()
        self.tc.track_metric("claude.success", 1, properties={"model": model})
        self.tc.track_metric("claude.tokens.input", input_tokens, properties={"model": model})
        self.tc.track_metric("claude.tokens.output", output_tokens, properties={"model": model})
    
    def on_error(self, error: Exception, model: str, context: dict = None):
        self.metrics.record_error(error, model, context)
        
        properties = {
            "error_type": type(error).__name__,
            "model": model,
            "message": str(error)[:200],
        }
        if isinstance(error, APIStatusError):
            properties["status_code"] = str(error.status_code)
        
        self.tc.track_event("claude_api_error", properties)
        self.tc.track_metric("claude.errors", 1, properties={"error_type": type(error).__name__})
        self.tc.flush()
    
    def on_retry(self, attempt: int, error: Exception, model: str):
        self.tc.track_event("claude_api_retry", {
            "attempt": str(attempt),
            "model": model,
            "error_type": type(error).__name__,
        })
```

---

## 10. Junior Walkthrough — Handle Your First Rate Limit

**Scenario**: Your code works in testing but fails in production with `RateLimitError`.

**Step 1: Understand what happened**

```python
# A RateLimitError means you've exceeded Anthropic's limits:
# - RPM (Requests Per Minute): Too many requests in 60 seconds
# - TPM (Tokens Per Minute): Too many tokens processed in 60 seconds
# 
# The API response includes a Retry-After header with how long to wait.
# NEVER retry immediately — you'll just get rate-limited again.
```

**Step 2: Add the simplest retry**

```python
import time
import anthropic
from anthropic import RateLimitError

client = anthropic.Anthropic()

def call_claude(question: str) -> str:
    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
                messages=[{"role": "user", "content": question}],
            )
            return response.content[0].text
        
        except RateLimitError as e:
            if attempt == 2:
                raise  # Give up after 3 attempts
            
            wait = 2 ** attempt + 1  # 1s, 3s, 7s
            print(f"Rate limited. Waiting {wait}s...")
            time.sleep(wait)
```

**Step 3: Use the production retry function from this file**

```python
# Replace your call with:
response = call_claude_with_retry(
    max_retries=5,
    model="claude-sonnet-4-6",
    max_tokens=512,
    messages=[{"role": "user", "content": question}],
)
```

**Step 4: Add the fallback for when all retries fail**

```python
def safe_call(question: str) -> str:
    try:
        return call_claude_with_retry(
            max_retries=5,
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": question}]
        ).content[0].text
    except Exception:
        return "I'm temporarily unavailable. Please speak with a team member."
```

---

## 11. Senior Patterns — Full Production Error Infrastructure

```python
class ProductionClaudeClient:
    """
    Production-hardened Claude client combining all patterns.
    
    Features:
    - Automatic retry with exponential backoff and jitter
    - Circuit breaker to prevent cascade failures
    - 3-tier graceful degradation
    - Timeout management per path type
    - Full Application Insights telemetry
    - Proactive context overflow prevention
    """
    
    def __init__(self, config: dict):
        self.breaker = CircuitBreaker(failure_threshold=5, reset_timeout=60)
        self.monitor = ClaudeErrorMonitor(config.get("appinsights_key", ""))
        self.assistant = ResilientRestaurantAssistant(LUMIERE_SYSTEM_PROMPT)
        self.failure_budget = ToolFailureBudget(max_failures_per_tool=3)
    
    async def chat(self, messages: list, path: str = "realtime_chat") -> dict:
        timeout = TIMEOUT_CONFIG.get(path, 20.0)
        
        try:
            response = await call_with_timeout(
                call_claude_async_with_retry(
                    max_retries=3,
                    model="claude-sonnet-4-6",
                    max_tokens=600,
                    messages=messages,
                ),
                timeout_seconds=timeout,
                path=path,
            )
            
            self.monitor.on_success(
                model="claude-sonnet-4-6",
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
            
            return {"text": response.content[0].text, "degraded": False, "tier": 1}
        
        except Exception as e:
            self.monitor.on_error(e, model="claude-sonnet-4-6")
            
            # Graceful degradation
            result = self.assistant.chat(
                messages[-1].get("content", "") if messages else "",
                messages,
            )
            return {**result, "original_error": type(e).__name__}
```

---

## 12. Tips, Tricks, and Gotchas

### Tips

1. **Log every error with model + token count** — the model string and prompt_tokens are the two most useful fields for debugging API errors
2. **Rate limits are per API key, not per process** — if multiple services share a key, one can starve the others
3. **Use `Retry-After` header, not a fixed delay** — Anthropic tells you exactly how long to wait; trust it
4. **Circuit breaker saves you during incidents** — without one, all your processes will hammer the API simultaneously when it recovers

### Tricks

5. **Test your retry logic** — use `unittest.mock` to simulate 429/500 and verify your code handles them correctly
6. **Separate rate limit errors from quality errors** — a malformed model response is not an API error; don't retry it
7. **Static fallbacks should be genuinely useful** — "I'm unavailable" is better than a confusing partial answer

### Gotchas

8. **Never retry 400/401/403/404** — these will never succeed without fixing the root cause
9. **Tool results MUST match tool_use IDs** — a missing or mismatched tool_result causes a 400 error, not a 500
10. **`is_error: True` in tool_result is different from raising an exception** — use `is_error: True` to tell Claude the tool failed; Claude will handle it gracefully. Raising an exception propagates to your code.
11. **Exponential backoff without jitter causes thundering herd** — if 10 processes all retry at exactly 2^N seconds, they all hit the API at the same time. Add `random.uniform(0, 1)` jitter.
12. **`BadRequestError` for context overflow has different messages** — check for "too long", "tokens", "context" in the error string rather than a specific code

---

## 13. Quick Reference Cheatsheet

```python
# ═══════════════════════════════════════════════════════════════
# ERROR HANDLING QUICK REFERENCE
# ═══════════════════════════════════════════════════════════════

# 1. ERROR CLASSIFICATION
RETRYABLE     = {429, 500, 529, "APIConnectionError", "APITimeoutError"}
NOT_RETRYABLE = {400, 401, 403, 404, 413}

# 2. RETRY WITH BACKOFF
for attempt in range(5):
    try:
        return client.messages.create(**kwargs)
    except RateLimitError as e:
        if attempt == 4: raise
        wait = min(float(e.response.headers.get("retry-after", 1)) * (2**attempt), 60)
        wait += random.uniform(0, 1)  # Jitter!
        time.sleep(wait)
    except APIStatusError as e:
        if e.status_code not in {429, 500, 529} or attempt == 4: raise
        time.sleep(min(2**attempt, 60))
    except BadRequestError: raise  # Never retry 400s

# 3. CIRCUIT BREAKER
breaker = CircuitBreaker(failure_threshold=5, reset_timeout=60)
try:
    response = breaker.call(client.messages.create, **kwargs)
except CircuitBreakerOpenError:
    return static_fallback()

# 4. CONTEXT OVERFLOW
except BadRequestError as e:
    if "too long" in str(e).lower():
        messages = messages[2:]  # Remove oldest pair; retry
    else:
        raise

# 5. 3-TIER FALLBACK
try:   response = call_primary_model(...)   # Tier 1: Sonnet
except:
    try: response = call_fallback_model(...) # Tier 2: Haiku
    except: response = static_response()    # Tier 3: Static

# 6. TIMEOUT
await asyncio.wait_for(coro, timeout=TIMEOUT_CONFIG["realtime_chat"])

# 7. TOOL ERRORS — always return a result
try:
    return tool_result_success(id, executor(**input))
except Exception as e:
    return tool_result_error(id, str(e))  # Never leave tool_use without result!

# 8. MONITORING
monitor.on_success(model, input_tokens, output_tokens)
monitor.on_error(exception, model, context)

# 9. TIMEOUT CONFIG
TIMEOUT_CONFIG = {
    "realtime_chat":    10.0,
    "rag_query":        20.0,
    "agent_step":       30.0,
    "agent_total":     120.0,
    "document_summary": 60.0,
}
```
