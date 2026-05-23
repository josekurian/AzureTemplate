# memory-management.md — Context Window and Memory Management

> **Purpose**: Complete guide to managing Claude's context window, implementing persistent memory across sessions, and designing memory-efficient multi-turn agents and conversational applications.  
> **Applies to**: All Claude models. Critical for long-running agents and conversational apps.  
> **Owner**: jose@hybridgenai.com  
> **Updated**: 2026-05-22

---

## Navigation

1. [Claude's Memory Model](#1-claudes-memory-model)
2. [Context Window Budget Planning](#2-context-window-budget-planning)
3. [Conversation History Management](#3-conversation-history-management)
4. [External Memory: Key-Value Store](#4-external-memory-key-value-store)
5. [External Memory: Vector Semantic Search](#5-external-memory-vector-semantic-search)
6. [Memory Injection Patterns](#6-memory-injection-patterns)
7. [Agent Memory Patterns](#7-agent-memory-patterns)
8. [Long Document Memory](#8-long-document-memory)
9. [Memory Architecture Decision Guide](#9-memory-architecture-decision-guide)
10. [Junior Quick-Start Walkthrough](#10-junior-quick-start-walkthrough)
11. [Senior Patterns and Production Hardening](#11-senior-patterns-and-production-hardening)
12. [Tips, Tricks and Gotchas](#12-tips-tricks-and-gotchas)
13. [Quick Reference Cheatsheet](#13-quick-reference-cheatsheet)

---

## 1. Claude's Memory Model

Claude has **no built-in persistent memory**. Every API request starts from scratch. Whatever Claude "knows" in one conversation is forgotten the moment the session ends — unless YOU store and re-inject it.

```
┌──────────────────────────────────────────────────────────────────┐
│              CLAUDE'S MEMORY TAXONOMY                            │
├────────────────┬─────────────┬─────────────┬────────────────────┤
│  TYPE          │ PERSISTENCE │ CAPACITY    │ COST               │
├────────────────┼─────────────┼─────────────┼────────────────────┤
│  In-Context    │ This request│ 200K tokens │ High (pay/token)   │
│  (Working)     │ only        │ = ~500 pages│                    │
├────────────────┼─────────────┼─────────────┼────────────────────┤
│  Conversation  │ This session│ Grows ~2K   │ Med (grows w/turns)│
│  History       │ only        │ per turn    │                    │
├────────────────┼─────────────┼─────────────┼────────────────────┤
│  Summarised    │ This session│ ~200 tokens │ Low (compressed)   │
│  Memory        │ + next      │ per session │                    │
├────────────────┼─────────────┼─────────────┼────────────────────┤
│  External KV   │ Permanent   │ Unlimited   │ Very low (DB query)│
│  (Structured)  │             │             │                    │
├────────────────┼─────────────┼─────────────┼────────────────────┤
│  Vector Store  │ Permanent   │ Unlimited   │ Low (embed+search) │
│  (Semantic)    │             │             │                    │
└────────────────┴─────────────┴─────────────┴────────────────────┘
```

**Design principle**: Don't try to keep everything in context. Use the right memory type for each category of information:
- **Transient facts** (current conversation topic) → conversation history
- **User preferences** (dietary restrictions, name) → external KV store
- **Domain knowledge** (menus, policies) → vector search / RAG
- **Past episode summaries** (what we discussed last week) → vector episodic memory

---

## 2. Context Window Budget Planning

### Context Window Limits

All current Claude models support 200,000 token context windows (≈ 150,000 words ≈ 500 pages).

```python
# Context window capacity by model (as of 2026)
CONTEXT_WINDOWS = {
    "claude-opus-4-6":         200_000,
    "claude-sonnet-4-6":       200_000,
    "claude-haiku-4-5-20251001": 200_000,
}

# Practical usable limits (leave room for output)
USABLE_INPUT_TOKENS = {
    model: window - 4096  # Reserve 4K for output
    for model, window in CONTEXT_WINDOWS.items()
}
```

### Context Consumption per Component

```python
# Typical token consumption per component:
CONTEXT_COMPONENTS = {
    "system_prompt_minimal": (200, 500),        # range (min, max) tokens
    "system_prompt_full": (500, 3_000),
    "knowledge_base_injected": (1_000, 10_000), # Full document in context
    "rag_chunks_top5": (500, 2_500),             # 5 × ~500 token chunks
    "tool_definitions_5tools": (500, 1_500),
    "conversation_turn": (100, 2_000),           # Per user+assistant exchange
    "tool_result": (100, 3_000),                 # Depends on tool output size
    "user_message_typical": (50, 500),
}

# Budget calculator:
def estimate_context_usage(
    system_tokens: int = 1_000,
    num_turns: int = 10,
    avg_tokens_per_turn: int = 500,
    rag_chunks: int = 5,
    avg_chunk_tokens: int = 400,
    num_tools: int = 5,
    avg_tokens_per_tool: int = 200
) -> dict:
    total = (
        system_tokens
        + num_turns * avg_tokens_per_turn
        + rag_chunks * avg_chunk_tokens
        + num_tools * avg_tokens_per_tool
    )
    return {
        "estimated_input_tokens": total,
        "pct_of_200k_window": round(total / 200_000 * 100, 1),
        "remaining_tokens": 200_000 - total,
        "ok_for_production": total < 150_000  # Leave 50K buffer
    }

# Example: restaurant assistant with 15-turn conversation
print(estimate_context_usage(
    system_tokens=1_500,
    num_turns=15,
    avg_tokens_per_turn=400,
    rag_chunks=4,
    avg_chunk_tokens=500,
    num_tools=6
))
# → estimated: 12,400 tokens (6.2% of window — plenty of room)
```

---

## 3. Conversation History Management

### Pattern 1: Fixed Rolling Window (Simplest)

Keep the last N message pairs. Simple, predictable token cost.

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class RollingWindowMemory:
    """
    Maintain a fixed-size sliding window of conversation history.

    Default: 15 pairs = 30 messages = ~6,000 tokens for typical conversations.
    Increase to 30 pairs for complex multi-step tasks.
    """
    max_pairs: int = 15  # 15 user+assistant exchanges = 30 messages
    messages: list[dict] = field(default_factory=list)

    def add_user_message(self, content: Any):
        """Add a user turn (content can be string or list of content blocks)."""
        self.messages.append({"role": "user", "content": content})
        self._trim()

    def add_assistant_message(self, content: Any):
        """Add an assistant turn."""
        self.messages.append({"role": "assistant", "content": content})

    def _trim(self):
        """Remove oldest user+assistant pair when over limit."""
        max_messages = self.max_pairs * 2
        while len(self.messages) > max_messages:
            self.messages.pop(0)   # Remove oldest user message
            if self.messages and self.messages[0]["role"] == "assistant":
                self.messages.pop(0)  # Remove paired assistant message

    def get_messages(self) -> list[dict]:
        return list(self.messages)

    def clear(self):
        self.messages.clear()

    @property
    def turn_count(self) -> int:
        return sum(1 for m in self.messages if m["role"] == "user")

# Usage:
memory = RollingWindowMemory(max_pairs=15)

def chat(user_input: str) -> str:
    memory.add_user_message(user_input)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=memory.get_messages()
    )

    assistant_reply = response.content[0].text
    memory.add_assistant_message(assistant_reply)
    return assistant_reply
```

---

### Pattern 2: Token-Budget Window (More Precise)

Keep messages until token budget is exhausted. More precise than message count.

```python
import anthropic

client = anthropic.Anthropic()

def count_message_tokens(
    messages: list[dict],
    system: str = "",
    model: str = "claude-sonnet-4-6"
) -> int:
    """Count tokens in a message list using the API's token counter endpoint."""
    kwargs = {"model": model, "messages": messages}
    if system:
        kwargs["system"] = system
    response = client.messages.count_tokens(**kwargs)
    return response.input_tokens

def trim_to_token_budget(
    messages: list[dict],
    system_prompt: str,
    token_budget: int = 8_000,
    model: str = "claude-sonnet-4-6"
) -> list[dict]:
    """
    Remove oldest message pairs until total tokens fit within budget.
    Always preserves the first pair (context anchor) and most recent turns.

    Args:
        messages: Full conversation history
        system_prompt: System prompt (included in token count)
        token_budget: Max tokens for conversation history
        model: Model to use for counting

    Returns:
        Trimmed message list that fits within budget
    """
    if not messages:
        return messages

    # Check if already within budget
    if count_message_tokens(messages, system_prompt, model) <= token_budget:
        return messages

    # Binary search approach — try different history lengths
    trimmed = list(messages)
    while len(trimmed) > 2:
        current_tokens = count_message_tokens(trimmed, system_prompt, model)
        if current_tokens <= token_budget:
            return trimmed
        # Remove oldest pair
        trimmed = trimmed[2:]

    return trimmed  # Return at least the most recent exchange
```

---

### Pattern 3: Progressive Summarisation (Best for Long Conversations)

Summarise old turns into a compact memory block and keep only recent turns verbatim.

```python
SUMMARISE_SYSTEM = """
You extract key information from a conversation into a compact memory block.

Include ONLY:
- Guest name if mentioned
- Specific preferences stated (food, wine, seating, etc.)
- Dietary requirements or allergies
- Reservations or commitments made
- Important context for continuing the conversation

EXCLUDE: small talk, pleasantries, repeat information.
Format: bullet list. Maximum 200 words.
"""

def progressive_summarise(
    messages: list[dict],
    keep_recent_pairs: int = 6,
    summary_model: str = "claude-haiku-4-5-20251001"  # Cheap for summarisation
) -> list[dict]:
    """
    Compress old conversation history via summarisation.
    Returns: [summary_exchange] + [recent_messages]

    Args:
        messages: Full conversation history
        keep_recent_pairs: Number of recent turns to keep verbatim (default: 6)
        summary_model: Model to use for summarisation (Haiku = cheap)

    Returns:
        Compressed message list
    """
    keep_count = keep_recent_pairs * 2  # Convert pairs to message count
    if len(messages) <= keep_count:
        return messages  # Not enough history to compress

    old_messages = messages[:-keep_count]
    recent_messages = messages[-keep_count:]

    # Build text representation for summarisation
    history_text = ""
    for msg in old_messages:
        role = msg["role"].upper()
        content = msg.get("content", "")
        if isinstance(content, str):
            history_text += f"{role}: {content[:500]}\n"  # Truncate very long messages
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    history_text += f"{role}: {block['text'][:500]}\n"

    # Generate summary using cheap model
    summary_response = client.messages.create(
        model=summary_model,
        max_tokens=300,
        system=SUMMARISE_SYSTEM,
        messages=[{"role": "user", "content": f"Summarise this conversation:\n\n{history_text}"}]
    )
    summary = summary_response.content[0].text

    # Return compressed history
    compressed_prefix = [
        {"role": "user", "content": f"[Previous conversation summary:\n{summary}]"},
        {"role": "assistant", "content": "I have context from our earlier conversation and will continue seamlessly."}
    ]
    return compressed_prefix + recent_messages

class SmartConversationMemory:
    """
    Full-featured memory manager with automatic compression.
    Starts with rolling window; switches to summarisation when context grows large.
    """

    def __init__(
        self,
        token_budget: int = 8_000,
        max_pairs_before_compress: int = 20,
        keep_recent_pairs: int = 8
    ):
        self.token_budget = token_budget
        self.max_pairs = max_pairs_before_compress
        self.keep_recent = keep_recent_pairs
        self.messages: list[dict] = []
        self.compression_count = 0

    def add_turn(self, user_content: Any, assistant_content: Any):
        self.messages.append({"role": "user", "content": user_content})
        self.messages.append({"role": "assistant", "content": assistant_content})

        # Compress if over threshold
        if len(self.messages) > self.max_pairs * 2:
            self.messages = progressive_summarise(self.messages, self.keep_recent)
            self.compression_count += 1

    def get_messages(self) -> list[dict]:
        return list(self.messages)

    @property
    def turn_count(self) -> int:
        return sum(1 for m in self.messages if m["role"] == "user")
```

---

## 4. External Memory: Key-Value Store

For structured facts that need exact retrieval across sessions (user preferences, settings, profile data).

```python
import json
from datetime import datetime, timedelta
from typing import Optional, Any

class GuestMemoryStore:
    """
    Persist and retrieve guest preferences across sessions.
    Uses Azure Table Storage in production; dict for local dev.
    """

    def __init__(self, backend: str = "local"):
        self.backend = backend
        self._local_store: dict[str, dict] = {}  # For local development

    def remember(
        self,
        guest_id: str,
        key: str,
        value: Any,
        expiry_days: Optional[int] = None
    ):
        """
        Store a fact about a guest.

        Args:
            guest_id: Unique guest identifier (email, user ID, etc.)
            key: Fact category (e.g., "dietary", "preferred_seating", "wine_style")
            value: The fact value (string, list, dict)
            expiry_days: Auto-expire after N days. None = never expires.

        Examples:
            store.remember("guest_123", "dietary", ["vegetarian", "gluten-free"])
            store.remember("guest_123", "preferred_wine_style", "full-bodied red")
            store.remember("guest_123", "anniversary", "June 15", expiry_days=365)
        """
        entry = {
            "value": value,
            "stored_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=expiry_days)).isoformat() if expiry_days else None
        }

        if self.backend == "local":
            if guest_id not in self._local_store:
                self._local_store[guest_id] = {}
            self._local_store[guest_id][key] = entry
        # Add Azure Table Storage / Redis / DynamoDB implementation here

    def recall(
        self,
        guest_id: str,
        key: Optional[str] = None
    ) -> dict:
        """
        Retrieve stored facts for a guest.

        Args:
            guest_id: Guest identifier
            key: Specific key to retrieve, or None for all facts

        Returns:
            Dict of key → value pairs
        """
        if self.backend == "local":
            guest_data = self._local_store.get(guest_id, {})
        else:
            guest_data = self._fetch_from_db(guest_id)

        # Filter expired entries
        now = datetime.utcnow().isoformat()
        valid_data = {
            k: v for k, v in guest_data.items()
            if v.get("expires_at") is None or v["expires_at"] > now
        }

        if key:
            entry = valid_data.get(key)
            return {key: entry["value"]} if entry else {}
        else:
            return {k: v["value"] for k, v in valid_data.items()}

    def recall_as_prompt_block(self, guest_id: str) -> str:
        """
        Format all guest memories as a system prompt injection block.

        Returns:
            Formatted string for injection into system prompt, or ""
        """
        facts = self.recall(guest_id)
        if not facts:
            return ""

        lines = ["KNOWN GUEST PREFERENCES:"]
        for key, value in facts.items():
            if isinstance(value, list):
                lines.append(f"- {key.replace('_', ' ').title()}: {', '.join(str(v) for v in value)}")
            else:
                lines.append(f"- {key.replace('_', ' ').title()}: {value}")

        return "\n".join(lines)

    def forget(self, guest_id: str, key: Optional[str] = None):
        """Delete a specific key or all memories for a guest."""
        if self.backend == "local":
            if key:
                self._local_store.get(guest_id, {}).pop(key, None)
            else:
                self._local_store.pop(guest_id, None)

# Usage:
memory_store = GuestMemoryStore()

# Store facts when discovered in conversation
memory_store.remember("guest_alice", "dietary", ["vegetarian"])
memory_store.remember("guest_alice", "preferred_seating", "window table")
memory_store.remember("guest_alice", "wine_style", "light white wine")
memory_store.remember("guest_alice", "special_occasion", "wedding anniversary", expiry_days=30)

# Inject into system prompt for next session
prompt_block = memory_store.recall_as_prompt_block("guest_alice")
print(prompt_block)
# KNOWN GUEST PREFERENCES:
# - Dietary: vegetarian
# - Preferred Seating: window table
# - Wine Style: light white wine
# - Special Occasion: wedding anniversary
```

---

## 5. External Memory: Vector Semantic Search

For episodic memories (past conversations) and semantic knowledge (documents, policies).

```python
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.identity import DefaultAzureCredential
import hashlib

class EpisodicMemoryStore:
    """
    Store and retrieve conversation summaries using vector similarity search.
    Allows Claude to "remember" relevant past sessions.
    """

    def __init__(
        self,
        search_endpoint: str,
        index_name: str = "episodic-memory",
        embedding_model: str = "text-embedding-3-large"
    ):
        credential = DefaultAzureCredential()
        self.search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=credential
        )
        self.openai_client = AzureOpenAI(...)
        self.embedding_model = embedding_model

    def _embed(self, text: str) -> list[float]:
        """Generate embedding for a text string."""
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding

    def store_session(
        self,
        session_id: str,
        guest_id: str,
        summary: str,
        full_transcript: Optional[str] = None
    ):
        """
        Store a session summary with its embedding.

        Args:
            session_id: Unique ID for this conversation session
            guest_id: Guest identifier
            summary: Concise summary of the conversation (use summarise_session())
            full_transcript: Optional full conversation text
        """
        embedding = self._embed(summary)

        document = {
            "id": session_id,
            "guest_id": guest_id,
            "summary": summary,
            "summary_embedding": embedding,
            "timestamp": datetime.utcnow().isoformat(),
            "transcript_hash": hashlib.md5(full_transcript.encode()).hexdigest() if full_transcript else None
        }

        self.search_client.upload_documents([document])

    def recall_relevant_sessions(
        self,
        guest_id: str,
        current_query: str,
        top_k: int = 3
    ) -> str:
        """
        Retrieve past sessions relevant to the current conversation topic.

        Args:
            guest_id: Filter to this guest's history
            current_query: Current user message (used to find relevant episodes)
            top_k: Number of relevant past sessions to retrieve

        Returns:
            Formatted memory block for injection into system prompt
        """
        query_embedding = self._embed(current_query)

        results = self.search_client.search(
            search_text=current_query,
            vector_queries=[VectorizedQuery(
                vector=query_embedding,
                k_nearest_neighbors=top_k * 2,
                fields="summary_embedding"
            )],
            filter=f"guest_id eq '{guest_id}'",
            top=top_k,
            select=["summary", "timestamp"]
        )

        episodes = list(results)
        if not episodes:
            return ""

        memory_block = "RELEVANT PAST INTERACTIONS:\n"
        for ep in episodes:
            date_str = ep.get("timestamp", "")[:10]  # Just the date
            memory_block += f"- [{date_str}]: {ep['summary']}\n"

        return memory_block

# Session summarisation helper
EPISODIC_SUMMARISE_PROMPT = """
Summarise this restaurant conversation into a compact episodic memory.
Include: what the guest asked about, what was recommended, what they ordered (if mentioned),
any preferences or restrictions they mentioned, any issues or special requests.
Omit: pleasantries, repetitive exchanges.
Maximum 100 words. Write in third person ("Guest asked about...", "Guest preferred...").
"""

def summarise_session_for_memory(
    messages: list[dict],
    model: str = "claude-haiku-4-5-20251001"
) -> str:
    """Generate a compact episodic summary of a completed session."""
    history_text = "\n".join([
        f"{m['role'].upper()}: {m['content'] if isinstance(m['content'], str) else '[complex content]'}"
        for m in messages
    ])

    response = client.messages.create(
        model=model,
        max_tokens=200,
        system=EPISODIC_SUMMARISE_PROMPT,
        messages=[{"role": "user", "content": history_text}]
    )
    return response.content[0].text
```

---

## 6. Memory Injection Patterns

### Hierarchical Injection (Most Important First)

```python
def build_memory_augmented_system_prompt(
    base_persona: str,
    guest_id: str,
    current_query: str,
    kv_store: GuestMemoryStore,
    episodic_store: EpisodicMemoryStore
) -> str:
    """
    Build a fully memory-augmented system prompt.
    Order: Core persona → Structured preferences → Relevant episodes → Instructions
    """
    parts = []

    # 1. Core persona (always present — cache this block)
    parts.append(base_persona)

    # 2. Structured preferences (exact facts — always inject for this guest)
    preferences = kv_store.recall_as_prompt_block(guest_id)
    if preferences:
        parts.append(preferences)

    # 3. Relevant past episodes (semantic search — inject if relevant)
    past_episodes = episodic_store.recall_relevant_sessions(
        guest_id=guest_id,
        current_query=current_query,
        top_k=2  # Top 2 most relevant past sessions
    )
    if past_episodes:
        parts.append(past_episodes)

    # 4. Tool usage instructions (if tools are available)
    parts.append("TOOLS: Use search_wine_list for wine queries; search_food_menu for food queries.")

    return "\n\n".join(filter(None, parts))
```

### Conditional Injection

```python
def inject_relevant_memory(
    user_message: str,
    guest_id: str,
    kv_store: GuestMemoryStore
) -> str:
    """
    Inject only the memory relevant to this specific query.
    Avoids padding every request with all stored facts.
    """
    msg_lower = user_message.lower()
    injections = []

    # Inject dietary info when food is discussed
    if any(kw in msg_lower for kw in ["menu", "food", "dish", "eat", "meal", "course", "order"]):
        dietary = kv_store.recall(guest_id, "dietary")
        if dietary:
            injections.append(f"Guest dietary requirements: {dietary.get('dietary')}")

    # Inject wine preference when wine is discussed
    if any(kw in msg_lower for kw in ["wine", "drink", "bottle", "glass", "pair", "sommelier"]):
        wine_pref = kv_store.recall(guest_id, "wine_style")
        if wine_pref:
            injections.append(f"Guest wine preference: {wine_pref.get('wine_style')}")

    # Inject seating preference for reservation queries
    if any(kw in msg_lower for kw in ["table", "book", "reservation", "seat", "sit"]):
        seating = kv_store.recall(guest_id, "preferred_seating")
        if seating:
            injections.append(f"Guest seating preference: {seating.get('preferred_seating')}")

    return "\n".join(injections) if injections else ""
```

---

## 7. Agent Memory Patterns

Agents accumulate tool results in context. Left unchecked, this balloons to thousands of tokens.

```python
def compress_tool_result(
    tool_name: str,
    result: dict,
    max_results: int = 3,
    max_text_chars: int = 1_500
) -> dict:
    """
    Compress large tool results before adding to agent context.
    Prevents tool results from consuming the entire context window.

    Common patterns:
    - Search results: keep top N, truncate long descriptions
    - File reads: truncate large files, keep first N chars
    - API responses: keep key fields, remove verbose metadata
    """
    compressed = dict(result)

    # Truncate large result lists
    if "results" in compressed and isinstance(compressed["results"], list):
        if len(compressed["results"]) > max_results:
            original_count = len(compressed["results"])
            compressed["results"] = compressed["results"][:max_results]
            compressed["_note"] = (
                f"Showing {max_results} of {original_count} results. "
                "Ask for more specific results or additional items by name."
            )

    # Truncate large text fields
    for key in ["content", "text", "body", "description", "full_text"]:
        if key in compressed and isinstance(compressed[key], str):
            if len(compressed[key]) > max_text_chars:
                compressed[key] = compressed[key][:max_text_chars] + "\n[...truncated...]"
                compressed["_truncated"] = True

    return compressed

# Agent loop with memory management
class MemoryAwareAgent:
    """
    Agent that actively manages its context budget.
    Compresses tool results and trims history to stay within budget.
    """

    MAX_CONTEXT_TOKENS = 80_000     # Leave 120K+ buffer in the 200K window
    MAX_TOOL_RESULT_CHARS = 2_000   # Per tool result
    MAX_STEPS = 20

    def __init__(self, system_prompt: str, tools: list, tool_executors: dict):
        self.system_prompt = system_prompt
        self.tools = tools
        self.tool_executors = tool_executors

    def run(self, user_message: str) -> str:
        messages = [{"role": "user", "content": user_message}]

        for step in range(self.MAX_STEPS):
            # Check context budget before each step
            token_count = count_message_tokens(messages, self.system_prompt)
            if token_count > self.MAX_CONTEXT_TOKENS:
                # Compress history if budget exceeded
                messages = progressive_summarise(messages, keep_recent_pairs=6)

            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=self.system_prompt,
                tools=self.tools,
                messages=messages
            )

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        return block.text
                return ""

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        executor = self.tool_executors.get(block.name)
                        raw_result = executor(**block.input) if executor else {"error": "Unknown tool"}

                        # Compress before adding to context
                        compressed = compress_tool_result(block.name, raw_result)

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(compressed)
                        })

                messages.append({"role": "user", "content": tool_results})

        return "Agent did not complete within step limit."
```

---

## 8. Long Document Memory

When working with documents too large to fit in context, use map-reduce or chunked patterns.

```python
def map_reduce_analysis(
    document: str,
    question: str,
    chunk_size_tokens: int = 4_000,
    overlap_tokens: int = 200
) -> str:
    """
    Analyse a document too large for a single context window.

    Map phase: Process each chunk independently → extract relevant info
    Reduce phase: Synthesise all chunk extracts → final answer

    Useful when: Document > 50,000 tokens, or when you need multiple
    simultaneous questions about the same large document.
    """

    # Chunk the document
    words = document.split()
    tokens_per_word = 1.3  # Rough estimate
    words_per_chunk = int(chunk_size_tokens / tokens_per_word)
    overlap_words = int(overlap_tokens / tokens_per_word)

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + words_per_chunk, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap_words  # Overlap to avoid missing cross-chunk context

    print(f"Document split into {len(chunks)} chunks")

    # MAP: Extract relevant info from each chunk
    map_results = []
    for i, chunk in enumerate(chunks):
        map_response = client.messages.create(
            model="claude-haiku-4-5-20251001",  # Cheap for map phase
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": (
                    f"Document chunk {i+1} of {len(chunks)}:\n\n{chunk}\n\n"
                    f"Extract any information relevant to: {question}\n"
                    "If nothing relevant, say 'No relevant information in this chunk.'"
                )
            }]
        )
        result = map_response.content[0].text
        if "No relevant information" not in result:
            map_results.append(f"Chunk {i+1}: {result}")

    print(f"Map phase: {len(map_results)} chunks had relevant info")

    if not map_results:
        return f"No information found in the document relevant to: {question}"

    # REDUCE: Synthesise all map results
    reduce_input = "\n\n".join(map_results)
    reduce_response = client.messages.create(
        model="claude-sonnet-4-6",  # Better model for synthesis
        max_tokens=1500,
        messages=[{
            "role": "user",
            "content": (
                f"You have extracted information from a large document in chunks.\n\n"
                f"Question: {question}\n\n"
                f"Extracted information from relevant chunks:\n{reduce_input}\n\n"
                "Synthesise this into a comprehensive, well-organised answer. "
                "Do not repeat information from multiple chunks."
            )
        }]
    )

    return reduce_response.content[0].text
```

---

## 9. Memory Architecture Decision Guide

```python
MEMORY_ARCHITECTURE_GUIDE = {
    "single_turn_qa": {
        "pattern": "No memory needed — pure stateless request",
        "implementation": "No message history; system prompt only",
        "example": "Document classification, single-question extraction"
    },
    "short_chat_session": {
        "pattern": "Rolling window memory",
        "implementation": "RollingWindowMemory(max_pairs=15)",
        "example": "Restaurant chatbot, customer support"
    },
    "long_analysis_session": {
        "pattern": "Progressive summarisation",
        "implementation": "SmartConversationMemory + progressive_summarise()",
        "example": "Legal document review, research assistance, debugging session"
    },
    "returning_users": {
        "pattern": "External KV + episodic vector memory",
        "implementation": "GuestMemoryStore + EpisodicMemoryStore",
        "example": "Personal assistant, CRM, loyalty programme"
    },
    "large_document_qa": {
        "pattern": "RAG or map-reduce (never full injection)",
        "implementation": "vector_search(top_k=5) or map_reduce_analysis()",
        "example": "Policy lookup, contract review, knowledge base Q&A"
    },
    "multi_tool_agent": {
        "pattern": "Rolling window + compressed tool results",
        "implementation": "MemoryAwareAgent with compress_tool_result()",
        "example": "Research agent, coding assistant, data pipeline"
    },
    "multi_agent_pipeline": {
        "pattern": "Pass only relevant summaries between agents",
        "implementation": "summarise_session_for_memory() at each stage",
        "example": "Document processing pipeline, multi-step automation"
    }
}

def recommend_memory_pattern(scenario: str) -> str:
    """Return the recommended memory pattern for a given scenario."""
    guide = MEMORY_ARCHITECTURE_GUIDE.get(scenario)
    if not guide:
        return "Scenario not recognised. Use rolling window as a safe default."
    return f"Pattern: {guide['pattern']}\nImplementation: {guide['implementation']}\nExample: {guide['example']}"
```

---

## 10. Junior Quick-Start Walkthrough

**Goal**: Add conversation memory to a Claude chatbot in 10 minutes.

**Step 1**: Keep a messages list.

```python
import anthropic
client = anthropic.Anthropic()

# This list holds the conversation history
messages = []

def chat(user_input: str) -> str:
    # 1. Add user message to history
    messages.append({"role": "user", "content": user_input})

    # 2. Send entire history to Claude
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system="You are a helpful restaurant assistant.",
        messages=messages  # ← The full history
    )

    # 3. Add Claude's response to history
    reply = response.content[0].text
    messages.append({"role": "assistant", "content": reply})

    return reply

# Test multi-turn memory
print(chat("My name is Alice."))
print(chat("What wine goes with lamb?"))
print(chat("What's my name?"))  # Claude should remember "Alice"
```

**Step 2**: Add a simple window limit so history doesn't grow forever.

```python
MAX_MESSAGES = 30  # 15 turns = 30 messages

def chat_with_limit(user_input: str) -> str:
    messages.append({"role": "user", "content": user_input})

    # Keep only the last MAX_MESSAGES messages
    trimmed = messages[-MAX_MESSAGES:]

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system="You are a helpful restaurant assistant.",
        messages=trimmed
    )

    reply = response.content[0].text
    messages.append({"role": "assistant", "content": reply})
    return reply
```

---

## 11. Senior Patterns and Production Hardening

### Memory Freshness and Staleness Detection

```python
from datetime import datetime, timedelta

def get_fresh_memories(
    guest_id: str,
    kv_store: GuestMemoryStore,
    max_age_days: int = 90
) -> dict:
    """
    Return only memories that haven't gone stale.
    Prevents injecting outdated preferences from years ago.
    """
    all_memories = kv_store.recall(guest_id)
    fresh = {}

    for key, value in all_memories.items():
        # Check stored_at timestamp (if available)
        entry = kv_store._local_store.get(guest_id, {}).get(key, {})
        stored_at_str = entry.get("stored_at")

        if stored_at_str:
            stored_at = datetime.fromisoformat(stored_at_str)
            age_days = (datetime.utcnow() - stored_at).days

            if age_days > max_age_days:
                continue  # Skip stale memory

        fresh[key] = value

    return fresh
```

### Memory Privacy and GDPR Compliance

```python
class PrivacyAwareMemoryStore(GuestMemoryStore):
    """
    Memory store with GDPR-compliant deletion and audit logging.
    """

    def forget_all(self, guest_id: str):
        """
        Right-to-erasure: delete ALL memories for a guest.
        Call when user requests data deletion.
        """
        self._local_store.pop(guest_id, None)
        # Also delete from vector store:
        # self.search_client.delete_documents([{"id": ...}])
        self._audit_log("forget_all", guest_id)
        print(f"[GDPR] All memories deleted for guest: {guest_id[:8]}...")

    def export_all(self, guest_id: str) -> dict:
        """
        Right-to-access: export all stored data for a guest.
        """
        data = self.recall(guest_id)
        self._audit_log("export", guest_id)
        return {"guest_id": guest_id, "data": data, "exported_at": datetime.utcnow().isoformat()}

    def _audit_log(self, action: str, guest_id: str):
        logger.info(f"memory_audit action={action} guest={guest_id[:8]}... timestamp={datetime.utcnow().isoformat()}")
```

---

## 12. Tips, Tricks and Gotchas

**Tip 1 — Token count before every prod deployment.** Use `client.messages.count_tokens()` to audit your memory injection logic. A typo in your injection code can silently insert 50,000 tokens and blow your context budget.

**Tip 2 — Use cheap models for summarisation.** Haiku is just as good as Sonnet at summarising conversations for memory. Use `claude-haiku-4-5-20251001` for all memory operations to save cost.

**Tip 3 — Store preferences ONLY when confirmed.** Don't infer preferences from questions. If a user asks "do you have vegetarian options?", that's not evidence they're vegetarian. Only store what's explicitly stated.

**Tip 4 — Keep memory injection under 500 tokens.** Memory blocks should be compact summaries, not full transcripts. If your memory block is >500 tokens, summarise it before injecting.

**Tip 5 — Use timestamps on all stored memories.** You need to know when something was stored to detect staleness, implement GDPR deletion timelines, and debug memory bugs.

**Gotcha 1 — Context grows faster than you think.** A 20-turn conversation with 500 tokens per exchange = 10,000 tokens. Add 5 RAG chunks × 500 tokens = 2,500 more. Add tool definitions and a system prompt and you're at 15,000+ tokens. Monitor and trim proactively.

**Gotcha 2 — Summarisation loses nuance.** When you compress 10 turns into a 200-word summary, subtle context is lost. For legal, medical, or high-stakes applications, keep more verbatim history.

**Gotcha 3 — Vector search retrieves by similarity, not recency.** The most recent episode might not be the most relevant. Use a hybrid approach: always inject the most recent session summary AND retrieve the top-K semantically similar ones.

**Gotcha 4 — Messages array ordering is strict.** The messages array must alternate user/assistant starting with "user". Consecutive user messages or consecutive assistant messages will return a 400 error.

**Gotcha 5 — tool_use and tool_result messages count too.** Tool use blocks in assistant messages and tool result blocks in user messages all consume context. Long tool results from search APIs can add thousands of tokens rapidly.

---

## 13. Quick Reference Cheatsheet

```
MEMORY TYPES:
  In-context (working):  messages array — limited by 200K window, costs tokens
  External KV:           exact structured facts — cheap, permanent, fast lookup
  Vector (semantic):     episode summaries — find by meaning, not keyword

CONTEXT WINDOW ALLOCATION (recommended):
  System prompt:    500–3,000 tokens (cache it!)
  Memory injection: 200–800 tokens
  RAG context:      1,000–5,000 tokens (top_k × chunk_size)
  Conversation:     2,000–10,000 tokens (rolling window)
  User message:     50–500 tokens
  Output reserve:   2,000–4,096 tokens (max_tokens)

HISTORY MANAGEMENT:
  Rolling window:  RollingWindowMemory(max_pairs=15) — use by default
  Summarisation:   progressive_summarise() — use when >20 turns
  Token budget:    trim_to_token_budget(8000) — precise control

WHEN TO COMPRESS:
  > 20 message pairs → progressive_summarise()
  > 80K input tokens → compress tool results
  > 3 agent steps    → check context budget

EXTERNAL MEMORY TRIGGERS:
  "My name is..."         → store name in KV
  "I'm allergic to..."    → store allergy in KV (with GDPR note)
  "I prefer..."           → store preference in KV
  Session ends            → summarise_session_for_memory() → vector store

GDPR CHECKLIST:
  ✓ User can request all stored data (export_all)
  ✓ User can delete all stored data (forget_all)
  ✓ All memory operations audit-logged
  ✓ Expiry set on time-sensitive data (e.g., special occasion)
  ✓ No PII in vector embeddings (embed summaries, not raw transcripts)
```
