# context-management.md — Managing Claude's Context Window

> **Purpose**: Complete strategies for efficiently using Claude's 200K context window across agents, RAG, and multi-turn conversations. Covers budget planning, dynamic injection, trimming algorithms, large document handling, and monitoring patterns.
> **Who This Is For**: Junior developers learning context fundamentals; senior engineers building multi-turn systems at scale.
> **Owner**: jose@hybridgenai.com

---

## Navigation

1. [Context Window Budget Planning](#1-context-window-budget-planning)
2. [Context Priority Framework](#2-context-priority-framework)
3. [Context Monitoring and Token Counting](#3-context-monitoring-and-token-counting)
4. [Dynamic Context Injection](#4-dynamic-context-injection)
5. [History Trimming Algorithms](#5-history-trimming-algorithms)
6. [Progressive Summarization](#6-progressive-summarization)
7. [Large Document Handling](#7-large-document-handling)
8. [Agent Context Management](#8-agent-context-management)
9. [Context Efficiency Patterns](#9-context-efficiency-patterns)
10. [Junior Walkthrough — First Multi-Turn App](#10-junior-walkthrough--first-multi-turn-app)
11. [Senior Patterns — Production Context Pipeline](#11-senior-patterns--production-context-pipeline)
12. [Tips, Tricks, and Gotchas](#12-tips-tricks-and-gotchas)
13. [Quick Reference Cheatsheet](#13-quick-reference-cheatsheet)

---

## 1. Context Window Budget Planning

### 1.1 Total Budget Overview

```
Claude context window: 200,000 tokens total (all current models as of 2026)

Token ≈ 0.75 English words  (1,000 tokens ≈ 750 words ≈ 1.5 pages)
Token ≈ 3-4 characters in English text
Token ≈ 1-2 characters in code (denser tokenization)

200K tokens ≈ 150,000 words ≈ ~300 pages of text
```

### 1.2 Budget Allocation Template

```
┌───────────────────────────────────────────────────────────────────┐
│              RECOMMENDED CONTEXT BUDGET (per request)              │
├──────────────────────────────────┬────────────────┬───────────────┤
│ Component                        │ Conservative   │ Standard      │
├──────────────────────────────────┼────────────────┼───────────────┤
│ System prompt                    │  1,000 tokens  │  3,000 tokens │
│ Memory injection (guest profile) │    300 tokens  │  1,000 tokens │
│ RAG context (retrieved chunks)   │  2,000 tokens  │  5,000 tokens │
│ Conversation history             │  2,000 tokens  │  8,000 tokens │
│ Current user message             │    100 tokens  │    500 tokens │
│ Tool definitions                 │    500 tokens  │  2,000 tokens │
│ Tool results (accumulated)       │    500 tokens  │  3,000 tokens │
│ Output reservation               │  1,024 tokens  │  4,096 tokens │
├──────────────────────────────────┼────────────────┼───────────────┤
│ TOTAL (prompt + output)          │  7,424 tokens  │ 26,596 tokens │
│ % of 200K window used            │      3.7%      │     13.3%     │
└──────────────────────────────────┴────────────────┴───────────────┘

Practical reality: Most production requests use 10,000-30,000 tokens.
The 200K limit is valuable for:
  - Full codebase analysis
  - Long document summarization
  - Extended research tasks
  - Conversation sessions spanning many hours
```

### 1.3 Context Budget Dataclass

```python
from dataclasses import dataclass, field
import anthropic
import os

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

@dataclass
class ContextBudget:
    """
    Tracks token budget allocation across all context components.
    
    Use this to plan and validate your context allocation before sending
    a request. Prevents nasty surprises when requests exceed context limits.
    
    Args:
        model:            Claude model string (determines max tokens)
        output_reserved:  Tokens reserved for Claude's output (default: 2048)
    
    Usage:
        budget = ContextBudget(model="claude-sonnet-4-6")
        budget.allocate("system_prompt", 2500)
        budget.allocate("conversation_history", 8000)
        budget.allocate("rag_context", 4000)
        
        if budget.is_over_budget:
            print(f"Over budget by {budget.over_by} tokens!")
        
        print(budget.summary())
    """
    
    model: str = "claude-sonnet-4-6"
    output_reserved: int = 2048
    
    # Model context limits
    _MODEL_LIMITS: dict = field(default_factory=lambda: {
        "claude-opus-4-6": 200_000,
        "claude-sonnet-4-6": 200_000,
        "claude-haiku-4-5-20251001": 200_000,
    }, init=False, repr=False)
    
    _allocations: dict = field(default_factory=dict, init=False)
    
    @property
    def max_tokens(self) -> int:
        return self._MODEL_LIMITS.get(self.model, 200_000)
    
    @property
    def input_budget(self) -> int:
        """Tokens available for input (max minus output reservation)."""
        return self.max_tokens - self.output_reserved
    
    @property
    def total_allocated(self) -> int:
        return sum(self._allocations.values())
    
    @property
    def remaining(self) -> int:
        return self.input_budget - self.total_allocated
    
    @property
    def utilisation_pct(self) -> float:
        return round(self.total_allocated / self.input_budget * 100, 1)
    
    @property
    def is_over_budget(self) -> bool:
        return self.total_allocated > self.input_budget
    
    @property
    def over_by(self) -> int:
        return max(0, self.total_allocated - self.input_budget)
    
    def allocate(self, component: str, tokens: int):
        """Register a token allocation for a named component."""
        self._allocations[component] = tokens
    
    def summary(self) -> str:
        lines = [f"Context Budget ({self.model})", "─" * 40]
        for component, tokens in self._allocations.items():
            pct = tokens / self.input_budget * 100
            bar = "█" * int(pct / 2)
            lines.append(f"  {component:<28} {tokens:>6} tokens  {pct:>4.1f}%  {bar}")
        lines.append("─" * 40)
        lines.append(f"  {'TOTAL':<28} {self.total_allocated:>6} tokens  {self.utilisation_pct:>4.1f}%")
        lines.append(f"  {'REMAINING':<28} {self.remaining:>6} tokens")
        if self.is_over_budget:
            lines.append(f"  ⚠️  OVER BUDGET by {self.over_by} tokens!")
        return "\n".join(lines)


# Example usage for the Lumière restaurant chatbot:
budget = ContextBudget(model="claude-sonnet-4-6", output_reserved=1024)
budget.allocate("system_prompt",         2_800)  # Maître persona + rules
budget.allocate("guest_profile",           800)  # Dietary prefs, visit history
budget.allocate("wine_rag_chunks",       4_500)  # Top-5 wine search results
budget.allocate("conversation_history",  6_000)  # Last 10 turns
budget.allocate("current_question",        300)  # User's message
budget.allocate("tool_definitions",      1_200)  # 3 tools defined
print(budget.summary())
# Context Budget (claude-sonnet-4-6)
# ─────────────────────────────────────────
#   system_prompt             2800 tokens   1.4%  █
#   guest_profile              800 tokens   0.4%
#   wine_rag_chunks           4500 tokens   2.3%  █
#   conversation_history      6000 tokens   3.0%  █
#   current_question           300 tokens   0.2%
#   tool_definitions          1200 tokens   0.6%
# ─────────────────────────────────────────
#   TOTAL                    15600 tokens   7.9%
#   REMAINING               182400 tokens
```

---

## 2. Context Priority Framework

When context must be trimmed (long conversations, large RAG results), follow this strict priority order.

```
PRIORITY   COMPONENT                    ACTION
─────────────────────────────────────────────────────────────────
P1 (KEEP)  System prompt               NEVER trim — defines identity
P1 (KEEP)  Current user message        NEVER trim — what to respond to
P1 (KEEP)  Most recent assistant turn  NEVER trim — immediate context

P2 (TRIM LAST)
           Recent conversation (3-5 turns)  Keep until budget forces trim
           Top-K RAG chunks (ranks 1-3)     Keep until budget forces trim
           Critical tool results            Keep until budget forces trim

P3 (TRIM FIRST)
           Old conversation history         Remove oldest turns first
           Lower-ranked RAG chunks          Remove ranks 4+ first
           Verbose tool results             Summarize / truncate

P4 (COMPRESS)
           Medium-old history               Summarize into a single block
           Duplicate information            Deduplicate
           Formatting overhead              Strip markdown if space-critical
```

```python
from enum import IntEnum

class ContextPriority(IntEnum):
    MUST_KEEP = 1      # System prompt, current message
    KEEP_LAST = 2      # Recent history, top RAG
    TRIM_FIRST = 3     # Old history, low-rank RAG
    COMPRESS = 4       # Summarizable content

# Map message indices to priorities in a conversation
def assign_message_priorities(
    messages: list[dict],
    recent_turns: int = 4,
) -> list[tuple[dict, ContextPriority]]:
    """
    Assign trim priority to each message in a conversation.
    
    Args:
        messages:     Full conversation history
        recent_turns: How many recent turns to protect (default: 4)
    
    Returns:
        List of (message, priority) tuples
    
    Example:
        # 10-turn conversation
        messages = [user1, asst1, user2, asst2, ..., user10, asst10]
        prioritized = assign_message_priorities(messages, recent_turns=4)
        # user10, asst10, user9, asst9  → KEEP_LAST
        # user8, asst8, ...             → TRIM_FIRST
    """
    result = []
    n = len(messages)
    protected_from_end = recent_turns * 2  # Each "turn" is 2 messages
    
    for i, msg in enumerate(messages):
        turns_from_end = n - i
        if turns_from_end <= protected_from_end:
            priority = ContextPriority.KEEP_LAST
        elif turns_from_end <= protected_from_end + 4:
            priority = ContextPriority.COMPRESS
        else:
            priority = ContextPriority.TRIM_FIRST
        
        result.append((msg, priority))
    
    return result
```

---

## 3. Context Monitoring and Token Counting

### 3.1 Pre-Request Token Count

```python
def check_context_usage(
    messages: list[dict],
    system: str | list = "",
    model: str = "claude-sonnet-4-6",
    output_reserved: int = 2048,
) -> dict:
    """
    Count tokens BEFORE sending a request to avoid surprises.
    
    Uses the count_tokens API endpoint (free — no generation).
    
    Args:
        messages:        Conversation messages list
        system:          System prompt (string or list with cache_control)
        model:           Model to count for
        output_reserved: Tokens to reserve for output
    
    Returns:
        dict with input_tokens, limit, utilisation_pct, remaining, safe_to_send
    
    Example:
        info = check_context_usage(messages, SYSTEM_PROMPT)
        if not info["safe_to_send"]:
            messages = trim_oldest_messages(messages, fraction=0.3)
    """
    # count_tokens is a free API call — no billing, no generation
    count = client.messages.count_tokens(
        model=model,
        system=system,
        messages=messages,
    )
    
    MODEL_LIMITS = {
        "claude-opus-4-6":          200_000,
        "claude-sonnet-4-6":        200_000,
        "claude-haiku-4-5-20251001": 200_000,
    }
    limit = MODEL_LIMITS.get(model, 200_000)
    input_tokens = count.input_tokens
    usable = limit - output_reserved
    
    return {
        "input_tokens":    input_tokens,
        "limit":           limit,
        "output_reserved": output_reserved,
        "usable":          usable,
        "utilisation_pct": round(input_tokens / usable * 100, 1),
        "remaining":       usable - input_tokens,
        "safe_to_send":    input_tokens < usable * 0.85,  # 15% safety margin
        "warning":         input_tokens > usable * 0.70,  # 70% warning threshold
    }

# Usage:
info = check_context_usage(messages, SYSTEM_PROMPT)
print(f"Using {info['input_tokens']:,} / {info['usable']:,} tokens ({info['utilisation_pct']}%)")

if info["warning"]:
    print("⚠️  Context getting large — consider trimming soon")

if not info["safe_to_send"]:
    print("🔴 Context too large — trim before sending!")
    messages = trim_messages_to_budget(messages, target_tokens=50_000)
```

### 3.2 Real-Time Context Monitor

```python
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ContextMonitor:
    """
    Monitor context usage across a multi-turn conversation session.
    
    Tracks token growth over time, warns when approaching limits,
    and logs usage for cost analysis.
    
    Args:
        model:              Model being used
        warn_threshold_pct: Warn when context exceeds this % (default: 60%)
        trim_threshold_pct: Trigger trim when exceeds this % (default: 80%)
    """
    model: str = "claude-sonnet-4-6"
    warn_threshold_pct: float = 60.0
    trim_threshold_pct: float = 80.0
    
    _history: list[dict] = None
    
    def __post_init__(self):
        self._history = []  # [{turn, tokens, action}]
    
    def check(self, messages: list, system: str = "") -> dict:
        """Check current usage and return recommended action."""
        info = check_context_usage(messages, system, self.model)
        turn = len([m for m in messages if m["role"] == "user"])
        
        self._history.append({
            "turn": turn,
            "input_tokens": info["input_tokens"],
            "utilisation_pct": info["utilisation_pct"],
        })
        
        action = "continue"
        reason = ""
        
        if info["utilisation_pct"] >= self.trim_threshold_pct:
            action = "trim_aggressive"
            reason = f"Context at {info['utilisation_pct']}% — aggressive trim needed"
            logger.warning(reason)
        elif info["utilisation_pct"] >= self.warn_threshold_pct:
            action = "trim_gentle"
            reason = f"Context at {info['utilisation_pct']}% — gentle trim recommended"
            logger.info(reason)
        
        return {**info, "action": action, "reason": reason, "turn": turn}
    
    def growth_rate(self) -> float:
        """Average token growth per turn."""
        if len(self._history) < 2:
            return 0.0
        delta = self._history[-1]["input_tokens"] - self._history[0]["input_tokens"]
        turns = self._history[-1]["turn"] - self._history[0]["turn"]
        return delta / max(turns, 1)
    
    def turns_until_limit(self) -> int:
        """Estimate how many more turns before context limit."""
        rate = self.growth_rate()
        if rate <= 0:
            return 999
        current_tokens = self._history[-1]["input_tokens"] if self._history else 0
        remaining = check_context_usage([], "", self.model)["usable"] - current_tokens
        return max(0, int(remaining / rate))
```

---

## 4. Dynamic Context Injection

Not all context should be present in every request. Inject selectively based on query intent to save tokens and improve relevance.

### 4.1 Query-Driven Context Builder

```python
from typing import Optional
import re

class DynamicContextBuilder:
    """
    Build context blocks relevant to the current query.
    
    Instead of always including the full wine list, staff handbook,
    booking rules, etc., injects only what's relevant to the current question.
    
    Args:
        search_client:  Azure AI Search client for RAG retrieval
        assets:         PromptAssets (lazy-loaded static content)
    
    Token savings:
        Full context (always inject all): ~15,000 tokens/request
        Dynamic injection:               ~5,000 tokens/request (67% reduction)
    """
    
    # Patterns for detecting query intent
    _WINE_PATTERNS    = re.compile(r"\b(wine|bottle|glass|red|white|rosé|pairing|sommelier|vintage|grape|tannin|chablis|bordeaux|champagne)\b", re.I)
    _BOOKING_PATTERNS = re.compile(r"\b(book|reservation|table|availability|cancel|change|deposit|party|group)\b", re.I)
    _MENU_PATTERNS    = re.compile(r"\b(menu|dish|food|eat|starter|main|dessert|tasting|course|chef|kitchen|special)\b", re.I)
    _ALLERGY_PATTERNS = re.compile(r"\b(allerg|intoleran|vegan|vegetarian|gluten|nut|dairy|kosher|halal)\b", re.I)
    _POLICY_PATTERNS  = re.compile(r"\b(policy|procedure|staff|training|rule|guideline|protocol)\b", re.I)
    
    def __init__(self, search_client, assets):
        self.search = search_client
        self.assets = assets
    
    def build(
        self,
        query: str,
        guest_id: Optional[str] = None,
        include_compact_menu: bool = True,
    ) -> tuple[str, dict]:
        """
        Build context string for the given query.
        
        Args:
            query:               User's question
            guest_id:            Guest ID for profile injection
            include_compact_menu: Always include compact menu (default: True)
        
        Returns:
            (context_string, metadata)
            metadata includes which sections were injected and token estimates
        
        Usage:
            context, meta = builder.build("Do you have a Merlot?", guest_id="G42")
            print(f"Injected: {meta['sections']}")  # ["compact_menu", "wine_context", "guest_profile"]
        """
        parts = []
        sections_injected = []
        
        # ── Always include: compact menu overview ─────────────────────
        if include_compact_menu:
            compact = self.assets.compact_menu  # ~500 tokens
            parts.append(f"<menu_overview>\n{compact}\n</menu_overview>")
            sections_injected.append("compact_menu")
        
        # ── Conditionally inject based on query patterns ───────────────
        
        if self._WINE_PATTERNS.search(query):
            # Retrieve top-5 wine chunks via hybrid search
            wine_results = self.search.hybrid_search(
                query,
                document_type="wine_list",
                top_k=5,
            )
            wine_text = self._format_search_results(wine_results)
            parts.append(f"<wine_context>\n{wine_text}\n</wine_context>")
            sections_injected.append("wine_context")
        
        if self._MENU_PATTERNS.search(query) and not self._WINE_PATTERNS.search(query):
            menu_results = self.search.hybrid_search(query, document_type="menu", top_k=3)
            parts.append(f"<menu_detail>\n{self._format_search_results(menu_results)}\n</menu_detail>")
            sections_injected.append("menu_detail")
        
        if self._ALLERGY_PATTERNS.search(query):
            allergy_info = self.assets.allergen_matrix  # Pre-formatted allergen table
            parts.append(f"<allergen_info>\n{allergy_info}\n</allergen_info>")
            sections_injected.append("allergen_info")
        
        if self._POLICY_PATTERNS.search(query):
            policy_results = self.search.hybrid_search(query, document_type="staff_handbook", top_k=3)
            parts.append(f"<policy_context>\n{self._format_search_results(policy_results)}\n</policy_context>")
            sections_injected.append("policy_context")
        
        if self._BOOKING_PATTERNS.search(query):
            booking_rules = self.assets.booking_policy  # ~300 tokens
            parts.append(f"<booking_policy>\n{booking_rules}\n</booking_policy>")
            sections_injected.append("booking_policy")
        
        # ── Guest profile (if identified) ──────────────────────────────
        if guest_id:
            profile = self._load_guest_profile(guest_id)
            if profile:
                parts.append(f"<guest_profile>\n{profile}\n</guest_profile>")
                sections_injected.append("guest_profile")
        
        context = "\n\n".join(parts)
        metadata = {
            "sections": sections_injected,
            "estimated_tokens": len(context) // 4,  # Rough estimate
            "query": query[:100],
        }
        
        return context, metadata
    
    def _format_search_results(self, results: list) -> str:
        """Format search results into readable context."""
        formatted = []
        for i, result in enumerate(results, 1):
            score = result.get("@search.score", 0)
            text = result.get("content", "")[:800]  # Truncate each chunk
            source = result.get("source_file", "unknown")
            formatted.append(f"[{i}] {text}\n   Source: {source} (relevance: {score:.2f})")
        return "\n\n".join(formatted)
    
    def _load_guest_profile(self, guest_id: str) -> str:
        """Load and format guest profile from storage."""
        try:
            profile = get_guest_profile(guest_id)  # Azure Table Storage lookup
            if not profile:
                return ""
            return (
                f"Name: {profile.get('name', 'Guest')}\n"
                f"Visit count: {profile.get('visit_count', 1)}\n"
                f"Dietary restrictions: {profile.get('dietary', 'None noted')}\n"
                f"Preferred wines: {profile.get('wine_pref', 'Not specified')}\n"
                f"Last visit: {profile.get('last_visit', 'First visit')}"
            )
        except Exception:
            return ""
```

---

## 5. History Trimming Algorithms

### 5.1 Rolling Window (Simplest)

```python
def rolling_window_messages(
    messages: list[dict],
    max_pairs: int = 12,
) -> list[dict]:
    """
    Keep only the most recent N conversation turns.
    
    This is the simplest trimming strategy — just a sliding window.
    Works well for most chat applications.
    
    Args:
        messages:   Full conversation history (alternating user/assistant)
        max_pairs:  Maximum user/assistant pairs to keep (default: 12)
    
    Returns:
        Trimmed messages list
    
    Example:
        15 turns → keep last 12 → discard first 3
    
    Cost savings:
        1,500 tokens/turn × 3 discarded turns = 4,500 tokens saved
        At $0.003/1K tokens (Sonnet) = $0.0135 per request saved
    """
    # Keep pairs — each pair is 2 messages (user + assistant)
    max_messages = max_pairs * 2
    
    if len(messages) <= max_messages:
        return messages  # No trimming needed
    
    # Always keep even number of messages (preserve user/assistant pairing)
    trimmed = messages[-max_messages:]
    
    # Ensure we start with a user message
    if trimmed and trimmed[0]["role"] == "assistant":
        trimmed = trimmed[1:]
    
    return trimmed
```

### 5.2 Token-Budget Trimming (Precise)

```python
def trim_messages_to_budget(
    messages: list[dict],
    target_tokens: int = 8_000,
    model: str = "claude-sonnet-4-6",
    protect_recent_turns: int = 3,
) -> list[dict]:
    """
    Trim conversation history to fit within a token budget.
    
    Removes oldest messages first while protecting recent turns.
    Uses the count_tokens API for precise measurement.
    
    Args:
        messages:             Full conversation history
        target_tokens:        Target token count for history (default: 8,000)
        model:                Model for token counting
        protect_recent_turns: Always keep this many recent turns (default: 3)
    
    Returns:
        Trimmed messages list
    
    Example:
        20-turn conversation, 15,000 tokens
        → trim to 8,000 tokens
        → removes oldest turns until under budget
        → always keeps last 3 turns (6 messages) regardless
    """
    if not messages:
        return messages
    
    protected = protect_recent_turns * 2  # Convert turns to messages
    protected_messages = messages[-protected:] if len(messages) > protected else messages
    trimmable = messages[:-protected] if len(messages) > protected else []
    
    while trimmable:
        # Count current tokens
        current_count = client.messages.count_tokens(
            model=model,
            messages=trimmable + protected_messages,
        ).input_tokens
        
        if current_count <= target_tokens:
            break
        
        # Remove oldest 2 messages (one user/assistant pair)
        trimmable = trimmable[2:] if len(trimmable) >= 2 else []
    
    return trimmable + protected_messages
```

### 5.3 Smart Trim with Type Awareness

```python
def smart_trim(
    messages: list[dict],
    max_tokens: int = 10_000,
    model: str = "claude-sonnet-4-6",
) -> list[dict]:
    """
    Intelligent trimming that compresses rather than just removes.
    
    Strategy:
    1. Keep last 4 turns as-is (most important)
    2. Compress turns 5-8 into 1-line summaries
    3. Remove anything older than turn 8
    
    Args:
        messages:   Full conversation history
        max_tokens: Target token budget for history
        model:      Model for token counting
    
    Returns:
        Trimmed/compressed messages list
    """
    if not messages:
        return messages
    
    # Separate into zones
    n = len(messages)
    recent = messages[max(0, n-8):]     # Last 4 turns — keep full
    middle = messages[max(0, n-16):max(0, n-8)]  # 4-8 turns ago — compress
    # Older: discard entirely
    
    # Compress middle zone into a summary message
    if middle:
        summary_text = _summarize_turns(middle)
        summary_message = {
            "role": "user",
            "content": f"[Earlier conversation summary: {summary_text}]"
        }
        compressed = [summary_message] + recent
    else:
        compressed = recent
    
    return compressed

def _summarize_turns(messages: list[dict]) -> str:
    """Create a brief 2-3 sentence summary of older turns using Haiku."""
    turns_text = "\n".join([
        f"{m['role'].upper()}: {str(m.get('content', ''))[:200]}"
        for m in messages
    ])
    
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",  # Cheap model for compression
        max_tokens=150,
        messages=[{
            "role": "user",
            "content": f"Summarize these conversation turns in 2-3 sentences. Keep key facts only.\n\n{turns_text}"
        }]
    )
    return response.content[0].text
```

---

## 6. Progressive Summarization

For very long sessions, summarize older history rather than discard it.

```python
from dataclasses import dataclass, field

@dataclass
class ProgressiveSummarizer:
    """
    Progressively summarize conversation history as it grows.
    
    Pattern:
    - While history < COMPRESS_AFTER turns: keep full history
    - When history hits COMPRESS_AFTER: compress oldest batch with Haiku
    - Result: rolling summary + recent turns (always fits in budget)
    
    Args:
        compress_after_turns: When to trigger compression (default: 20)
        keep_recent_turns:    Recent turns to always keep full (default: 5)
        summary_model:        Model for compression (default: Haiku for cost)
    
    Token budget impact:
        Without: 20 turns × 1,500 tokens/turn = 30,000 tokens
        With:    3,000 token summary + 5 × 1,500 = 10,500 tokens (65% reduction)
    """
    
    compress_after_turns: int = 20
    keep_recent_turns: int = 5
    summary_model: str = "claude-haiku-4-5-20251001"
    
    _messages: list[dict] = field(default_factory=list, init=False)
    _summary: str = field(default="", init=False)
    _total_turns: int = field(default=0, init=False)
    
    def add_user(self, text: str):
        """Add a user message."""
        self._messages.append({"role": "user", "content": text})
    
    def add_assistant(self, text: str):
        """Add an assistant message. Increments turn counter."""
        self._messages.append({"role": "assistant", "content": text})
        self._total_turns += 1
        
        # Check if we need to compress
        if self._total_turns > 0 and self._total_turns % self.compress_after_turns == 0:
            self._compress_history()
    
    def get_messages_for_api(self) -> list[dict]:
        """
        Get the messages to send to Claude.
        
        If there's a summary, injects it as the first user message.
        Always includes the most recent turns in full.
        """
        recent = self._messages[-(self.keep_recent_turns * 2):]
        
        if self._summary:
            summary_injection = {
                "role": "user",
                "content": f"[Conversation history summary: {self._summary}]"
            }
            return [summary_injection] + recent
        
        return recent
    
    def _compress_history(self):
        """Compress old messages into a summary using Haiku."""
        # Get messages to compress (all except recent)
        recent_count = self.keep_recent_turns * 2
        to_compress = self._messages[:-recent_count] if len(self._messages) > recent_count else []
        
        if not to_compress:
            return
        
        # Build summary prompt
        history_text = "\n".join([
            f"{m['role'].upper()}: {str(m.get('content', ''))[:300]}"
            for m in to_compress
        ])
        
        if self._summary:
            compress_prompt = f"""Existing summary: {self._summary}

New conversation turns to incorporate:
{history_text}

Create an updated summary in 3-5 sentences. Keep: guest preferences, key decisions, important facts."""
        else:
            compress_prompt = f"""Summarize these conversation turns in 3-5 sentences. Keep: key topics, decisions, guest preferences, important facts.

{history_text}"""
        
        response = client.messages.create(
            model=self.summary_model,
            max_tokens=300,
            messages=[{"role": "user", "content": compress_prompt}]
        )
        
        # Update summary; keep only recent messages in full
        self._summary = response.content[0].text
        self._messages = self._messages[-recent_count:]
        
        print(f"Compressed {len(to_compress)} messages into summary ({len(self._summary)} chars)")
```

---

## 7. Large Document Handling

### 7.1 Map-Reduce for Documents Larger Than Context

```python
def analyse_large_document(
    document: str,
    question: str,
    chunk_tokens: int = 6_000,
    map_model: str = "claude-haiku-4-5-20251001",
    reduce_model: str = "claude-sonnet-4-6",
) -> str:
    """
    Analyse documents that are larger than the context window.
    
    Uses Map-Reduce pattern:
    1. SPLIT: Divide document into chunks
    2. MAP:   Extract relevant info from each chunk (Haiku — cheap)
    3. REDUCE: Synthesize all extractions into final answer (Sonnet — quality)
    
    Args:
        document:     Full document text
        question:     What to analyze/answer
        chunk_tokens: Target tokens per chunk (default: 6,000)
        map_model:    Model for mapping phase (default: Haiku for cost)
        reduce_model: Model for reduce phase (default: Sonnet for quality)
    
    Returns:
        Final synthesized answer
    
    Cost example:
        100-page document = ~75,000 tokens
        Map phase:   13 chunks × 6K tokens × $0.000375/K = $0.029 (Haiku)
        Reduce phase: 1 × ~3K tokens × $0.003/K = $0.009 (Sonnet)
        Total: ~$0.038 vs $0.225 for full Sonnet processing
    """
    # Step 1: Split document into overlapping chunks
    chunks = _split_into_chunks(document, chunk_tokens=chunk_tokens, overlap=200)
    print(f"Document: {len(document):,} chars → {len(chunks)} chunks")
    
    # Step 2: Map — extract relevant info from each chunk
    chunk_extractions = []
    
    for i, chunk in enumerate(chunks):
        extraction = client.messages.create(
            model=map_model,
            max_tokens=400,
            messages=[{
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"Extract ONLY information from the text below that is directly relevant "
                    f"to answering the question. If nothing is relevant, respond with exactly: "
                    f"'NOT_RELEVANT'\n\n"
                    f"Text (section {i+1}/{len(chunks)}):\n{chunk}"
                )
            }]
        ).content[0].text
        
        if "NOT_RELEVANT" not in extraction.upper():
            chunk_extractions.append(f"[Section {i+1}]:\n{extraction}")
    
    print(f"Map complete: {len(chunk_extractions)}/{len(chunks)} sections had relevant info")
    
    if not chunk_extractions:
        return "No relevant information was found in the document for your question."
    
    # Step 3: Reduce — synthesize all extractions
    combined = "\n\n".join(chunk_extractions)
    
    # If combined extractions are still large, recurse
    combined_tokens = len(combined) // 4
    if combined_tokens > 40_000:
        return analyse_large_document(combined, question, chunk_tokens, map_model, reduce_model)
    
    final = client.messages.create(
        model=reduce_model,
        max_tokens=1_200,
        messages=[{
            "role": "user",
            "content": (
                f"Based on the following extracted sections from a document, "
                f"provide a comprehensive answer to: {question}\n\n"
                f"Extracted sections:\n{combined}"
            )
        }]
    )
    
    return final.content[0].text

def _split_into_chunks(text: str, chunk_tokens: int = 6_000, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks by character count."""
    chars_per_chunk = chunk_tokens * 4  # ~4 chars per token
    overlap_chars = overlap * 4
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + chars_per_chunk, len(text))
        
        # Try to end at a paragraph boundary
        if end < len(text):
            boundary = text.rfind('\n\n', start, end)
            if boundary > start + chars_per_chunk // 2:
                end = boundary + 2
        
        chunks.append(text[start:end])
        start = max(start + 1, end - overlap_chars)  # Overlap
    
    return chunks
```

### 7.2 Selective Context Loading

```python
async def load_context_for_query(
    query: str,
    available_documents: list[dict],
    max_tokens: int = 12_000,
) -> str:
    """
    Intelligently select which documents to load based on query relevance.
    
    Use when you have many potentially relevant documents but can't load them all.
    
    Args:
        query:               User's question
        available_documents: List of {id, title, summary, tokens} dicts
        max_tokens:          Total context token budget
    
    Returns:
        Context string with most relevant documents
    """
    # Step 1: Score documents by relevance using Haiku
    relevance_prompt = f"""Question: {query}

Rate each document's relevance to this question. Return JSON only:
[{{"id": "doc1", "score": 0-10, "reason": "one sentence"}}, ...]

Documents:
{json.dumps([{"id": d["id"], "title": d["title"], "summary": d["summary"]} for d in available_documents], indent=2)}"""
    
    scoring = await client_async.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": relevance_prompt}]
    )
    
    scores = json.loads(scoring.content[0].text)
    score_map = {s["id"]: s["score"] for s in scores}
    
    # Step 2: Greedy select documents by score until budget fills
    ranked = sorted(available_documents, key=lambda d: score_map.get(d["id"], 0), reverse=True)
    selected = []
    tokens_used = 0
    
    for doc in ranked:
        if doc.get("score", score_map.get(doc["id"], 0)) < 5:
            break  # Skip low-relevance documents
        if tokens_used + doc["tokens"] > max_tokens:
            continue  # Skip if it would exceed budget
        selected.append(doc)
        tokens_used += doc["tokens"]
    
    # Step 3: Load and format selected documents
    context_parts = []
    for doc in selected:
        content = load_document_content(doc["id"])
        context_parts.append(f"<document id='{doc['id']}' title='{doc['title']}'>\n{content}\n</document>")
    
    return "\n\n".join(context_parts)
```

---

## 8. Agent Context Management

Agents accumulate context through tool results and multi-step reasoning. Manage this carefully.

```python
MAX_TOOL_RESULT_CHARS = 2_000  # Per tool result
MAX_AGENT_HISTORY_TOKENS = 15_000  # Total agent loop history

def compress_tool_result_for_context(
    tool_name: str,
    raw_result: dict | list | str,
    max_chars: int = MAX_TOOL_RESULT_CHARS,
) -> str:
    """
    Compress a tool result to prevent context bloat in agent loops.
    
    Large tool results are a leading cause of agent context overflow.
    A search tool returning 50 results at 500 chars each = 25,000 chars.
    Compressing to top-5 at 200 chars each = 1,000 chars (96% reduction).
    
    Args:
        tool_name:  Name of the tool (for tool-specific logic)
        raw_result: The raw tool output
        max_chars:  Maximum characters in compressed output
    
    Returns:
        Compressed string ready for tool_result content
    """
    if isinstance(raw_result, str):
        if len(raw_result) <= max_chars:
            return raw_result
        return raw_result[:max_chars] + f"\n[...truncated. {len(raw_result) - max_chars} more chars]"
    
    if isinstance(raw_result, list):
        # Limit to first 5 items, truncate each item's string values
        compressed = []
        for item in raw_result[:5]:
            if isinstance(item, dict):
                compressed.append({
                    k: (v[:200] + "..." if isinstance(v, str) and len(v) > 200 else v)
                    for k, v in item.items()
                })
            else:
                compressed.append(item)
        
        result_str = json.dumps(compressed)
        if len(raw_result) > 5:
            result_str += f"\n[...{len(raw_result) - 5} more items omitted]"
        return result_str
    
    if isinstance(raw_result, dict):
        # Remove verbose/redundant fields based on tool type
        FIELDS_TO_REMOVE = {
            "search":  ["@odata.count", "@search.nextPageParameters", "metadata_storage_path"],
            "db":      ["_id", "__v", "created_at", "updated_at", "internal_id"],
            "default": ["debug", "trace", "raw_response", "_links"],
        }
        
        fields_to_drop = FIELDS_TO_REMOVE.get(tool_name.split("_")[0], FIELDS_TO_REMOVE["default"])
        cleaned = {k: v for k, v in raw_result.items() if k not in fields_to_drop}
        
        result_str = json.dumps(cleaned)
        if len(result_str) > max_chars:
            result_str = result_str[:max_chars] + "...}"
        return result_str
    
    return str(raw_result)[:max_chars]
```

---

## 9. Context Efficiency Patterns

### Summary Table

| Technique | Token Savings | Latency Impact | Complexity | Best For |
|-----------|--------------|----------------|------------|----------|
| Rolling window (last N turns) | 30–60% on long convos | None | Very Low | All multi-turn chat |
| Prompt caching (stable content) | 40–90% on cached read | −30% TTFT | Low | Repeated requests |
| Selective RAG injection | 50–80% vs full context | +20ms (routing) | Medium | Query-dependent context |
| RAG top-K = 3 (not 10) | 40% on RAG chunk size | None | Low | Document Q&A |
| Tool result compression | 20–80% in agent loops | None | Low | Agents with DB/search tools |
| Map-Reduce | Enables any doc size | 2–5× slower | High | Large document analysis |
| Progressive summarization | 60–80% on old history | +200ms (compress) | Medium | Long-running sessions |
| Context budget planning | Prevents overflow errors | None | Low | All production apps |

---

## 10. Junior Walkthrough — First Multi-Turn App

**Scenario**: Building a simple restaurant chatbot that remembers conversation context.

**Step 1: Start with a simple messages list**

```python
import anthropic

client = anthropic.Anthropic()
SYSTEM = "You are Maître, AI concierge for Lumière restaurant. Be warm and helpful."

messages = []  # Empty history

def chat(user_input: str) -> str:
    """Add user message, call Claude, add assistant reply, return text."""
    
    # Add user message to history
    messages.append({"role": "user", "content": user_input})
    
    # Call Claude with full history
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=SYSTEM,
        messages=messages,  # Pass entire history
    )
    
    assistant_text = response.content[0].text
    
    # Add assistant reply to history
    messages.append({"role": "assistant", "content": assistant_text})
    
    return assistant_text

# Multi-turn conversation
print(chat("Hi, I have a nut allergy. What can I eat?"))
# → Claude knows about nut allergy

print(chat("What about the tasting menu?"))
# → Claude STILL knows about nut allergy from previous turn
# This works because messages list has both turns!
```

**Step 2: Add basic trimming to prevent context overflow**

```python
MAX_HISTORY_PAIRS = 10  # Keep last 10 turns

def chat_with_trim(user_input: str) -> str:
    messages.append({"role": "user", "content": user_input})
    
    # Trim if too long
    if len(messages) > MAX_HISTORY_PAIRS * 2:
        messages[:] = messages[-(MAX_HISTORY_PAIRS * 2):]
        print(f"Trimmed history to last {MAX_HISTORY_PAIRS} turns")
    
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=SYSTEM,
        messages=messages,
    )
    
    assistant_text = response.content[0].text
    messages.append({"role": "assistant", "content": assistant_text})
    return assistant_text
```

**Step 3: Monitor token usage**

```python
def chat_monitored(user_input: str) -> str:
    messages.append({"role": "user", "content": user_input})
    
    # Check tokens BEFORE sending
    count = client.messages.count_tokens(model="claude-sonnet-4-6", system=SYSTEM, messages=messages)
    print(f"Sending {count.input_tokens:,} tokens ({count.input_tokens/200000*100:.1f}% of limit)")
    
    response = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=512, system=SYSTEM, messages=messages
    )
    messages.append({"role": "assistant", "content": response.content[0].text})
    return response.content[0].text
```

---

## 11. Senior Patterns — Production Context Pipeline

```python
class ProductionContextPipeline:
    """
    Full production context management pipeline.
    
    Integrates:
    - Dynamic injection (only relevant context per query)
    - Token monitoring (count before send)
    - Automatic trimming (rolling window + smart compression)
    - Caching (stable system prompt cached)
    - Monitoring (Application Insights telemetry)
    """
    
    def __init__(self, config: dict):
        self.context_builder = DynamicContextBuilder(
            search_client=AzureSearchClient(config),
            assets=PromptAssets(),
        )
        self.summarizer = ProgressiveSummarizer(
            compress_after_turns=20,
            keep_recent_turns=5,
        )
        self.monitor = ContextMonitor(warn_threshold_pct=60, trim_threshold_pct=80)
    
    async def respond(self, user_message: str, session: dict) -> str:
        # 1. Build dynamic context for this specific query
        context, meta = self.context_builder.build(
            query=user_message,
            guest_id=session.get("guest_id"),
        )
        
        # 2. Get trimmed/compressed history
        self.summarizer.add_user(user_message)
        messages = self.summarizer.get_messages_for_api()
        
        # 3. Check token budget
        system = self._build_cached_system(context)
        info = self.monitor.check(messages, system=str(system))
        
        if info["action"] == "trim_aggressive":
            messages = trim_messages_to_budget(messages, target_tokens=6_000)
        
        # 4. Call Claude with cached system prompt
        response = await client_async.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=system,
            messages=messages,
        )
        
        reply = response.content[0].text
        
        # 5. Update history
        self.summarizer.add_assistant(reply)
        
        return reply
    
    def _build_cached_system(self, dynamic_context: str) -> list[dict]:
        """Build system with cache_control on stable parts."""
        return [
            {
                "type": "text",
                "text": LUMIERE_BASE_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},  # Cache stable base
            },
            {
                "type": "text",
                "text": dynamic_context,
                # No cache on dynamic context — it changes per query
            }
        ]
```

---

## 12. Tips, Tricks, and Gotchas

### Tips

1. **Always count tokens before sending** — use `count_tokens` (free API call) to check budget before a request that might be large
2. **Cache the system prompt** — even at 500 tokens, it's cacheable. At 2,000+ tokens it pays off significantly
3. **Inject context selectively** — don't inject the full wine list on a booking question; use intent detection
4. **progressive summarization > deletion** — summarizing preserves intent; deleting loses context entirely

### Tricks

5. **Interleave summaries as user messages** — inject `[Summary: ...]` as a user message rather than modifying assistant messages (keeps conversation structure valid)
6. **Use XML tags for context sections** — `<wine_context>`, `<guest_profile>` — Claude respects XML boundaries and grounds its responses within them
7. **Compress tool results immediately** — never store the full raw API response in messages; always compress before appending
8. **count_tokens is free** — use it liberally for debugging; it doesn't trigger generation

### Gotchas

9. **Messages must start with "user"** — Claude API requires first message to have `"role": "user"`. If your history starts with assistant, remove it.
10. **Tool results must be tied to tool_use blocks** — a `tool_result` message must immediately follow the `assistant` message that contains the matching `tool_use` block, in the same user turn.
11. **200K is not a target, it's a limit** — requests near the 200K limit have high latency and cost. Target 20K–50K for most use cases.
12. **`count_tokens` includes tool definitions** — pass `tools=your_tools` to get an accurate count when using agents

---

## 13. Quick Reference Cheatsheet

```python
# ═══════════════════════════════════════════════════════════════
# CONTEXT MANAGEMENT QUICK REFERENCE
# ═══════════════════════════════════════════════════════════════

# 1. COUNT TOKENS BEFORE SENDING (free)
count = client.messages.count_tokens(model=MODEL, system=SYS, messages=msgs)
print(f"{count.input_tokens:,} tokens ({count.input_tokens/200000*100:.1f}% of limit)")

# 2. ROLLING WINDOW TRIM (simplest)
messages = messages[-(MAX_PAIRS * 2):]  # Keep last N pairs

# 3. TOKEN-BUDGET TRIM
while len(messages) > 4:
    if client.messages.count_tokens(model=M, messages=messages).input_tokens < 8000:
        break
    messages = messages[2:]  # Drop oldest pair

# 4. PROGRESSIVE SUMMARIZE (for 20+ turn sessions)
summarizer = ProgressiveSummarizer(compress_after_turns=20, keep_recent_turns=5)
summarizer.add_user(question); summarizer.add_assistant(reply)
msgs = summarizer.get_messages_for_api()

# 5. DYNAMIC INJECTION (only relevant context)
context, meta = context_builder.build(query=user_question, guest_id=guest_id)
# meta["sections"] → ["compact_menu", "wine_context"]

# 6. MAP-REDUCE FOR LARGE DOCS
answer = analyse_large_document(doc_text, question, chunk_tokens=6000)

# 7. COMPRESS TOOL RESULTS
compressed = compress_tool_result_for_context(tool_name, raw_result, max_chars=2000)

# 8. CONTEXT PRIORITY (what to keep when trimming)
# P1 KEEP:    system prompt, current user message, last assistant turn
# P2 KEEP:    recent 3-5 turns, top RAG chunks
# P3 TRIM:    old history (oldest first), low-rank RAG chunks
# P4 COMPRESS: medium-age history → summary

# 9. BUDGET TARGETS
# Chat widget:  8,000-15,000 tokens/request
# RAG query:   10,000-20,000 tokens/request
# Agent loop:  15,000-30,000 tokens/step
# Doc analysis: 50,000-100,000 tokens (map-reduce)

# 10. ALERT THRESHOLDS
# 60% of limit → warn + start gentle trim
# 80% of limit → aggressive trim / summarize
# 85% of limit → hard stop / reject request
```
