# agents.md — Claude Agent Patterns and Orchestration

> **Purpose**: Complete guide to designing, building, testing, and operating reliable Claude agents — from simple ReAct loops to multi-agent orchestration.  
> **Applies to**: Claude API, Claude Agent SDK, Claude Code, Cowork, custom agentic pipelines.  
> **Owner**: jose@hybridgenai.com  
> **Updated**: 2026-05-22

---

## Navigation

1. [What Makes an Agent Different](#1-what-makes-a-claude-agent-different-from-a-prompt)
2. [Agent Architecture Patterns](#2-agent-architecture-patterns)
3. [Building the ReAct Loop](#3-building-the-react-loop-step-by-step)
4. [Tool Design for Agents](#4-tool-design-best-practices)
5. [Memory Patterns](#5-memory-patterns-for-agents)
6. [Agent Reliability Patterns](#6-agent-reliability-patterns)
7. [Multi-Agent Orchestration](#7-multi-agent-orchestration)
8. [Agent System Prompt Design](#8-agent-system-prompt-design)
9. [Observability and Logging](#9-observability-and-logging)
10. [Testing Agents](#10-testing-agents)
11. [Cost Management for Agents](#11-cost-management-for-agents)
12. [Junior Quick-Start Walkthrough](#12-junior-quick-start-walkthrough)
13. [Senior Patterns and Production Hardening](#13-senior-patterns-and-production-hardening)
14. [Tips, Tricks and Gotchas](#14-tips-tricks-and-gotchas)
15. [Quick Reference Cheatsheet](#15-quick-reference-cheatsheet)

---

## 1. What Makes a Claude Agent Different from a Prompt

A **prompt** is stateless: one input → one output.  
An **agent** is a loop: Claude decides the next action, executes tools, observes results, and continues until the goal is met.

```
User Goal
    ↓
┌─────────────────────────────────────────┐
│         AGENT LOOP                       │
│                                          │
│  Claude reasons → selects tool/action    │
│       ↓                                  │
│  Tool executes → returns result          │
│       ↓                                  │
│  Result added to conversation context    │
│       ↓                                  │
│  Claude reasons again                    │
│       ↓                                  │
│  Repeat until stop_reason == "end_turn" │
└─────────────────────────────────────────┘
    ↓
Final answer delivered to user
```

**Key differences from a single prompt:**

| Dimension | Single Prompt | Agent |
|---|---|---|
| State | Stateless | Stateful (conversation history) |
| Actions | Text generation only | Text + tool calls |
| Loops | 1 API call | Multiple API calls |
| Cost | Predictable | Variable (depends on steps) |
| Error risk | Single point | Compounding across steps |
| Best for | Q&A, generation | Multi-step tasks, automation |

**The power is autonomy. The risk is compounding errors.** Good agent design minimises the blast radius of any single bad decision.

---

## 2. Agent Architecture Patterns

### Pattern A: Single-Agent ReAct Loop
**Best for**: Linear tasks with clear success criteria, single domain.

```
User Request → Claude (ReAct) → Tool A → Claude → Tool B → Claude → Answer
```

**Example use cases**: Search + summarise, fetch + format data, code + run + debug.

**Token cost**: Low per step; scales linearly with step count.

---

### Pattern B: Orchestrator + Subagents
**Best for**: Complex tasks that can be decomposed into parallel or sequential subtasks.

```
User Request
    ↓
Orchestrator (claude-opus-4-6 or claude-sonnet-4-6)
    ├─ Subagent A: Research subtask (claude-sonnet-4-6)
    ├─ Subagent B: Code generation (claude-sonnet-4-6)
    └─ Subagent C: Review/QA    (claude-haiku-4-5-20251001)
    ↓
Synthesised Result
```

**Key design rule**: The orchestrator handles decomposition and synthesis. Subagents handle execution only. This keeps each agent's context focused and reduces error propagation.

**Token cost**: Higher (multiple models running), but parallel execution reduces wall-clock time.

---

### Pattern C: Specialist Agents with Routing
**Best for**: Domains where a single agent would need a very broad, unfocused system prompt.

```
User Request → Router (Haiku, cheap) → dispatches to:
    ├─ Wine Expert Agent
    ├─ Kitchen Assistant Agent
    ├─ Reservations Agent
    └─ Manager Tools Agent
```

**Benefit**: Each agent has a tight, specialised system prompt → higher accuracy, lower cost.

---

### Pattern D: Human-in-the-Loop Agent
**Best for**: High-stakes decisions — financial transactions, medical recommendations, irreversible actions, legal documents.

```
Agent decides action
    ↓
Is action high-stakes? → YES → Request human approval
    ↓                              ↓ Approved
Execute                          Continue
    ↓ Denied
    Revise action
```

---

### Pattern E: Pipeline Agent
**Best for**: Document processing, data transformation, multi-stage workflows.

```
Input Document
    ↓
Stage 1: Extraction Agent  (extracts structured data)
    ↓
Stage 2: Validation Agent  (checks extracted data)
    ↓
Stage 3: Enrichment Agent  (adds calculated fields)
    ↓
Stage 4: Output Agent      (formats final output)
```

Each stage receives the output of the previous stage as its input. Errors at any stage fail fast and do not propagate silently.

---

## 3. Building the ReAct Loop Step by Step

### Minimal Working Agent

```python
import anthropic
import json

client = anthropic.Anthropic()

# Define tools
tools = [
    {
        "name": "search_knowledge_base",
        "description": "Search the restaurant knowledge base for menus, policies, wine list. Use for any factual question about Lumière.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search terms"},
                "top_k": {"type": "integer", "description": "Number of results to return. Default: 3"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_table_availability",
        "description": "Check table availability for a given date, time, and party size.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                "time": {"type": "string", "description": "Time in HH:MM format (24-hour)"},
                "party_size": {"type": "integer", "description": "Number of guests (1-20)"}
            },
            "required": ["date", "time", "party_size"]
        }
    }
]

# Tool executor map — wire tool names to real functions
def search_knowledge_base(query: str, top_k: int = 3) -> dict:
    """Replace with real vector search implementation."""
    return {"results": [{"text": f"Mock result for '{query}'", "score": 0.9}]}

def get_table_availability(date: str, time: str, party_size: int) -> dict:
    """Replace with real reservations API call."""
    return {"available": True, "date": date, "time": time, "party_size": party_size}

TOOL_EXECUTORS = {
    "search_knowledge_base": search_knowledge_base,
    "get_table_availability": get_table_availability,
}

def run_agent(user_message: str, system_prompt: str, max_steps: int = 20) -> str:
    """
    Full ReAct agent loop.

    Args:
        user_message: The user's initial request
        system_prompt: Agent persona and rules
        max_steps: Hard limit to prevent infinite loops (default: 20)

    Returns:
        Final text response from Claude
    """
    messages = [{"role": "user", "content": user_message}]
    step = 0

    while step < max_steps:
        step += 1

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system_prompt,
            tools=tools,
            messages=messages,
        )

        # Append Claude's full response to history (including tool_use blocks)
        messages.append({"role": "assistant", "content": response.content})

        # Termination condition
        if response.stop_reason == "end_turn":
            # Extract final text response
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""

        # Process tool calls
        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    print(f"  [Step {step}] Calling tool: {tool_name}({tool_input})")

                    executor = TOOL_EXECUTORS.get(tool_name)
                    if executor:
                        try:
                            result = executor(**tool_input)
                        except Exception as e:
                            result = {"success": False, "error": str(e)}
                    else:
                        result = {"success": False, "error": f"Unknown tool: {tool_name}"}

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })

            # Add all tool results back to conversation
            messages.append({"role": "user", "content": tool_results})

    # Exceeded max steps
    raise RuntimeError(f"Agent exceeded {max_steps} steps without completing task")

# Run it
result = run_agent(
    user_message="Is there a table for 4 available this Saturday at 7pm? And what should we order?",
    system_prompt="You are Maître, the AI concierge for Lumière restaurant. Help guests with reservations and menu questions."
)
print(result)
```

---

### Full Production ReAct Loop with Logging

```python
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

@dataclass
class AgentStep:
    step_number: int
    tool_name: str | None
    tool_input: dict | None
    tool_result: dict | None
    input_tokens: int
    output_tokens: int
    latency_ms: float

@dataclass
class AgentRun:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    user_message: str = ""
    final_response: str = ""
    total_steps: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_latency_ms: float = 0
    success: bool = False
    error: str | None = None
    steps: list[AgentStep] = field(default_factory=list)

def run_agent_with_telemetry(
    user_message: str,
    system_prompt: str,
    tools: list[dict],
    tool_executors: dict,
    session_id: str = "",
    max_steps: int = 20
) -> AgentRun:
    """Production agent loop with full telemetry tracking."""

    run = AgentRun(
        session_id=session_id,
        user_message=user_message
    )
    messages = [{"role": "user", "content": user_message}]

    try:
        for step_num in range(1, max_steps + 1):
            step_start = time.time()

            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=system_prompt,
                tools=tools,
                messages=messages,
            )

            step_latency = (time.time() - step_start) * 1000
            run.total_input_tokens += response.usage.input_tokens
            run.total_output_tokens += response.usage.output_tokens
            run.total_latency_ms += step_latency

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        run.final_response = block.text
                run.success = True
                run.total_steps = step_num
                break

            if response.stop_reason == "tool_use":
                tool_results = []

                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    tool_start = time.time()
                    executor = tool_executors.get(block.name)

                    try:
                        result = executor(**block.input) if executor else {
                            "success": False, "error": f"Unknown tool: {block.name}"
                        }
                    except Exception as e:
                        result = {"success": False, "error": str(e)}

                    tool_latency = (time.time() - tool_start) * 1000

                    run.steps.append(AgentStep(
                        step_number=step_num,
                        tool_name=block.name,
                        tool_input=block.input,
                        tool_result=result,
                        input_tokens=response.usage.input_tokens,
                        output_tokens=response.usage.output_tokens,
                        latency_ms=step_latency + tool_latency
                    ))

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })

                messages.append({"role": "user", "content": tool_results})

        else:
            run.success = False
            run.error = f"Exceeded max_steps={max_steps}"

    except Exception as e:
        run.success = False
        run.error = str(e)

    return run
```

---

## 4. Tool Design Best Practices

### Rule 1: Tools That Fail Loudly

Claude cannot recover from silent failures. Always return structured results.

```python
# ❌ BAD — silent failure
def search_menu(query: str) -> list:
    try:
        return db.search(query)
    except Exception:
        return []  # Claude sees empty list — thinks "no results", can't tell it's a failure

# ✅ GOOD — explicit success/failure envelope
def search_menu(query: str, course: str = None) -> dict:
    """
    Search the food menu.

    Returns:
        {
            "success": bool,
            "results": [{"name": str, "description": str, "price_gbp": float}],
            "count": int,
            "message": str,    # Guidance for Claude if results empty
            "error": str       # Only present on failure
        }
    """
    try:
        results = db.search(query=query, course=course)
        if not results:
            return {
                "success": True,
                "results": [],
                "count": 0,
                "message": f"No menu items found for '{query}'. Try broader terms or check the full menu."
            }
        return {"success": True, "results": results, "count": len(results)}
    except TimeoutError:
        return {"success": False, "error": "Menu database timed out. Please try again in a moment.", "error_code": "TIMEOUT"}
    except Exception as e:
        logger.error(f"search_menu failed: {e}", exc_info=True)
        return {"success": False, "error": "Search temporarily unavailable.", "error_code": "UNKNOWN"}
```

---

### Rule 2: Tool Descriptions Are Prompt Content

Claude reads tool descriptions as part of its reasoning. Vague descriptions cause wrong tool selection.

```python
# ❌ Vague
{
    "name": "search",
    "description": "Search for things"
}

# ✅ Precise — tells Claude WHEN to use it, WHAT it returns, and WHAT NOT to use it for
{
    "name": "search_wine_list",
    "description": (
        "Search the restaurant's curated wine list by producer name, grape variety, "
        "appellation (region), vintage year, or wine style. "
        "Use for ANY wine-related guest query. "
        "Returns: producer, wine name, vintage, appellation, style, glass/bottle price. "
        "Do NOT use for food menu queries — use search_food_menu instead."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query. Examples: 'Burgundy Pinot Noir', 'Château Margaux 2018', 'full-bodied red under £80', 'champagne'"
            },
            "max_price_gbp": {
                "type": "number",
                "description": "Maximum bottle price in GBP. Only include if guest stated a budget."
            },
            "food_pairing": {
                "type": "string",
                "description": "Dish being paired. Helps filter by style. E.g., 'beef wellington', 'halibut', 'cheese board'."
            }
        },
        "required": ["query"],
        "additionalProperties": False
    }
}
```

---

### Rule 3: Schema Completeness

```python
# Full schema template — copy and modify for each tool
{
    "name": "tool_name",          # Verb phrase: search_X, create_X, get_X, update_X
    "description": "...",         # When to use, what it returns, what NOT to use it for
    "input_schema": {
        "type": "object",
        "properties": {
            "required_param": {
                "type": "string",                    # string | number | integer | boolean | array | object
                "description": "What it is + example values"
            },
            "optional_enum_param": {
                "type": "string",
                "enum": ["option_a", "option_b", "option_c"],
                "description": "What each option means"
            },
            "optional_number": {
                "type": "number",
                "description": "Description. Default: 5. Range: 1–100."
            },
            "optional_array": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of X values. Maximum 10 items."
            }
        },
        "required": ["required_param"],   # Only truly required params here
        "additionalProperties": False      # Prevent hallucinated parameters
    }
}
```

---

### Rule 4: Tool Idempotency

Design tools to be safe to retry. If Claude calls a tool twice with the same input, it should produce the same result without side effects.

```python
# ❌ Non-idempotent — calling twice creates two records
def create_reservation(date: str, time: str, guests: int, email: str) -> dict:
    reservation_id = db.insert_reservation(date, time, guests, email)
    return {"reservation_id": reservation_id}

# ✅ Idempotent — checks for existing reservation first
def create_or_get_reservation(date: str, time: str, guests: int, email: str) -> dict:
    existing = db.find_reservation(email=email, date=date, time=time)
    if existing:
        return {"reservation_id": existing.id, "status": "already_exists", "created": False}
    reservation_id = db.insert_reservation(date, time, guests, email)
    return {"reservation_id": reservation_id, "status": "created", "created": True}
```

---

### Rule 5: Limit Tool Count

Each tool in the context costs tokens and increases Claude's decision space. For most agents, 5–8 tools is optimal. Beyond 12 tools, tool selection accuracy degrades.

```
1–4 tools:   High accuracy, fast reasoning
5–8 tools:   Optimal range for most use cases
9–12 tools:  Acceptable with very clear descriptions
12+ tools:   Consider routing to specialised sub-agents
```

---

## 5. Memory Patterns for Agents

### Memory Type 1: Working Memory (In-Context)

Conversation history lives in the `messages` array. Available automatically but consumes tokens as it grows.

```python
from collections import deque
from typing import Optional

class ConversationWindow:
    """
    Sliding window conversation history with token budget management.
    Keeps the most recent turns within a token budget.
    """

    def __init__(self, max_turns: int = 20, max_tokens: int = 40_000):
        self.messages: list[dict] = []
        self.max_turns = max_turns
        self.max_tokens = max_tokens

    def add_user(self, content: str):
        self.messages.append({"role": "user", "content": content})
        self._trim()

    def add_assistant(self, content):
        self.messages.append({"role": "assistant", "content": content})

    def add_tool_results(self, results: list[dict]):
        self.messages.append({"role": "user", "content": results})

    def _trim(self):
        """Remove oldest turns if over limit. Always keep at least 2 turns."""
        while len(self.messages) > self.max_turns * 2 and len(self.messages) > 4:
            # Remove oldest user+assistant pair
            self.messages.pop(0)
            if self.messages and self.messages[0]["role"] == "assistant":
                self.messages.pop(0)

    def get_messages(self) -> list[dict]:
        return self.messages.copy()
```

---

### Memory Type 2: Episodic Memory (Per-Session Summary)

At the end of each session, summarise key facts and store them for future retrieval.

```python
SUMMARISE_PROMPT = """
You are a concise note-taker. Extract the key facts from this conversation
that would be useful to know in a future conversation with the same guest.

Focus on:
- Guest preferences (food, wine, seating)
- Dietary restrictions or allergies
- Past orders or special occasions
- Any complaints or issues

Return a bullet-point summary under 100 words. Omit small talk.
"""

async def summarise_session(messages: list[dict], guest_id: str):
    """Summarise session and store for future retrieval."""
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",   # Cheap model for summarisation
        max_tokens=256,
        system=SUMMARISE_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Conversation to summarise:\n{json.dumps(messages, indent=2)}"
        }]
    )
    summary = response.content[0].text

    # Store in database with timestamp
    await memory_store.upsert(
        guest_id=guest_id,
        summary=summary,
        timestamp=datetime.utcnow().isoformat()
    )
    return summary

async def load_guest_memory(guest_id: str, limit: int = 3) -> str:
    """Load past session summaries to inject into system prompt."""
    summaries = await memory_store.get_recent(guest_id=guest_id, limit=limit)
    if not summaries:
        return ""

    memory_block = "GUEST HISTORY (from past visits):\n"
    for s in summaries:
        memory_block += f"- [{s.timestamp[:10]}]: {s.summary}\n"
    return memory_block
```

---

### Memory Type 3: Semantic Memory (Vector Search)

Long-term knowledge (menus, policies, wine lists) stored as embeddings and retrieved per query.

```python
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

def retrieve_knowledge(
    query: str,
    top_k: int = 5,
    document_type: str = None
) -> list[dict]:
    """
    Retrieve relevant knowledge base chunks using hybrid search.
    Called by the agent's search tool.
    """
    # Generate query embedding
    embedding_response = openai_client.embeddings.create(
        model="text-embedding-3-large",
        input=query
    )
    query_vector = embedding_response.data[0].embedding

    # Build filter
    filter_expr = f"document_type eq '{document_type}'" if document_type else None

    # Hybrid search: keyword + vector + semantic ranker
    results = search_client.search(
        search_text=query,
        vector_queries=[VectorizedQuery(
            vector=query_vector,
            k_nearest_neighbors=top_k * 2,  # Over-fetch, re-rank
            fields="content_vector"
        )],
        filter=filter_expr,
        query_type="semantic",
        semantic_configuration_name="lumiere-semantic",
        top=top_k,
        select=["title", "content", "document_type", "source_file", "page_number"]
    )

    return [
        {
            "title": r["title"],
            "content": r["content"],
            "source": f"{r['source_file']}, p.{r.get('page_number', '?')}",
            "score": r["@search.reranker_score"]
        }
        for r in results
    ]
```

---

## 6. Agent Reliability Patterns

### Pattern 1: Circuit Breaker

Prevent cascade failures when a downstream tool is failing repeatedly.

```python
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Blocking calls (too many failures)
    HALF_OPEN = "half_open" # Testing recovery

class CircuitBreaker:
    """
    Circuit breaker for agent tool calls.

    States:
        CLOSED:    Normal. Calls pass through. Failures counted.
        OPEN:      Too many failures. Calls blocked for `reset_timeout` seconds.
        HALF_OPEN: Allowing one test call to check if service recovered.

    Example:
        breaker = CircuitBreaker(name="wine_db", failure_threshold=3, reset_timeout=60)
        result = breaker.call(search_wine_list, query="pinot noir")
    """

    def __init__(self, name: str, failure_threshold: int = 3, reset_timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = CircuitState.CLOSED

    def call(self, fn, *args, **kwargs):
        """Call function through circuit breaker."""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                return {
                    "success": False,
                    "error": f"Service '{self.name}' temporarily unavailable (circuit open). Try again in a moment.",
                    "error_code": "CIRCUIT_OPEN"
                }

        try:
            result = fn(*args, **kwargs)
            # Success — reset
            self.failure_count = 0
            self.state = CircuitState.CLOSED
            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                print(f"[CircuitBreaker] {self.name} OPENED after {self.failure_count} failures")

            raise

# Usage
wine_db_breaker = CircuitBreaker(name="wine_database", failure_threshold=3, reset_timeout=60)

def safe_search_wine(query: str) -> dict:
    return wine_db_breaker.call(search_wine_list, query=query)
```

---

### Pattern 2: Exponential Backoff with Jitter

```python
import time
import random
from anthropic import RateLimitError, APIStatusError

def call_claude_with_retry(
    model: str,
    messages: list,
    system: str,
    tools: list | None = None,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0
) -> anthropic.types.Message:
    """
    Call Claude API with exponential backoff + jitter.

    Retry on:
        - RateLimitError (429): exponential backoff
        - APIStatusError 529 (overloaded): exponential backoff
        - Connection errors: fixed retry

    Do NOT retry:
        - 400 Bad Request (fix your request)
        - 401 Unauthorized (fix your API key)
        - 403 Forbidden (permissions issue)
    """
    for attempt in range(max_retries):
        try:
            kwargs = {
                "model": model,
                "max_tokens": 2048,
                "system": system,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools

            return client.messages.create(**kwargs)

        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            # Check Retry-After header if present
            retry_after = int(e.response.headers.get("retry-after", 0))
            if retry_after:
                delay = retry_after
            else:
                delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1.0), max_delay)
            print(f"Rate limited. Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(delay)

        except APIStatusError as e:
            if e.status_code == 529:  # Overloaded
                if attempt == max_retries - 1:
                    raise
                delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1.0), max_delay)
                print(f"API overloaded. Retrying in {delay:.1f}s")
                time.sleep(delay)
            else:
                raise  # Don't retry other 4xx/5xx errors
```

---

### Pattern 3: Max Step Guard

Every agent loop MUST have a hard step limit to prevent infinite loops.

```python
MAX_AGENT_STEPS = 25    # Default for complex agents
MAX_AGENT_STEPS_SIMPLE = 10  # For simple Q&A agents

for step in range(MAX_AGENT_STEPS):
    response = call_claude_with_retry(...)

    if response.stop_reason == "end_turn":
        break  # Normal termination
else:
    # This runs when the for loop completes without break
    raise AgentLoopError(
        f"Agent exceeded {MAX_AGENT_STEPS} steps. "
        f"Last tool called: {last_tool_name}. "
        f"Check for tool failure loop."
    )
```

---

### Pattern 4: Failure Budget per Tool

Some tools should not be retried more than N times in a single agent run.

```python
class ToolFailureBudget:
    """
    Track per-tool failure counts within a single agent run.
    Prevents Claude from spinning in a tool failure loop.
    """

    def __init__(self, budget_per_tool: int = 3):
        self.budget = budget_per_tool
        self.failures: dict[str, int] = {}

    def record_failure(self, tool_name: str) -> bool:
        """
        Record a failure. Returns True if budget exhausted.
        """
        self.failures[tool_name] = self.failures.get(tool_name, 0) + 1
        return self.failures[tool_name] >= self.budget

    def is_exhausted(self, tool_name: str) -> bool:
        return self.failures.get(tool_name, 0) >= self.budget

# Usage in agent loop:
budget = ToolFailureBudget(budget_per_tool=3)

for block in response.content:
    if block.type == "tool_use":
        if budget.is_exhausted(block.name):
            result = {
                "success": False,
                "error": f"Tool '{block.name}' has failed {budget.budget} times. Stopping retries.",
                "suggestion": "Please inform the user that this feature is temporarily unavailable."
            }
        else:
            try:
                result = tool_executors[block.name](**block.input)
            except Exception as e:
                budget.record_failure(block.name)
                result = {"success": False, "error": str(e)}
```

---

## 7. Multi-Agent Orchestration

### Orchestrator Implementation

```python
import asyncio
from typing import Callable

@dataclass
class SubagentTask:
    name: str
    system_prompt: str
    user_message: str
    tools: list[dict]
    tool_executors: dict
    model: str = "claude-sonnet-4-6"

async def run_subagent_async(task: SubagentTask) -> str:
    """Run a single subagent asynchronously."""
    # Note: Use async anthropic client for true async
    import anthropic
    async_client = anthropic.AsyncAnthropic()

    messages = [{"role": "user", "content": task.user_message}]

    for _ in range(15):  # Max 15 steps per subagent
        response = await async_client.messages.create(
            model=task.model,
            max_tokens=2048,
            system=task.system_prompt,
            tools=task.tools,
            messages=messages,
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
                    executor = task.tool_executors.get(block.name)
                    result = executor(**block.input) if executor else {"error": "Unknown tool"}
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result)
                    })
            messages.append({"role": "user", "content": tool_results})

    return "Subagent did not complete within step limit."

async def run_parallel_subagents(tasks: list[SubagentTask]) -> list[str]:
    """Run multiple subagents in parallel."""
    return await asyncio.gather(*[run_subagent_async(task) for task in tasks])

# Orchestrator that decomposes and runs tasks in parallel
ORCHESTRATOR_SYSTEM_PROMPT = """
You are an orchestrator. You receive a complex task and must:
1. Decompose it into 2-4 independent subtasks
2. Return a JSON list of subtask descriptions

Each subtask should be independently completable and not depend on other subtasks.
Return ONLY a JSON array: ["subtask 1 description", "subtask 2 description", ...]
"""

async def orchestrate(complex_task: str, subagent_factory: Callable) -> str:
    """
    Decompose a task, run subtasks in parallel, synthesise results.
    """
    # Step 1: Decompose
    decompose_response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=ORCHESTRATOR_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": complex_task}]
    )
    subtasks = json.loads(decompose_response.content[0].text)

    # Step 2: Run subtasks in parallel
    subagent_tasks = [subagent_factory(subtask) for subtask in subtasks]
    results = await run_parallel_subagents(subagent_tasks)

    # Step 3: Synthesise
    synthesis_prompt = f"""
Original task: {complex_task}

Results from subtasks:
{chr(10).join(f"Subtask {i+1}: {result}" for i, result in enumerate(results))}

Synthesise these results into a single coherent response to the original task.
"""
    synthesis = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": synthesis_prompt}]
    )
    return synthesis.content[0].text
```

---

## 8. Agent System Prompt Design

System prompts for agents differ from conversational assistant prompts. They need explicit guidance on tool selection, step limits, and failure handling.

```python
RESTAURANT_AGENT_SYSTEM_PROMPT = """
You are Maître, an AI concierge agent for Lumière restaurant.

TASK EXECUTION PROCESS:
1. Understand what the guest is asking
2. Decide which tools (if any) are needed
3. Call tools one at a time; observe results before deciding next action
4. Synthesise tool results into a helpful, conversational response
5. Never reveal tool names, API calls, or system internals to the guest

TOOL SELECTION RULES:
- search_wine_list: ONLY for wine queries (pairing, recommendations, availability)
- search_food_menu: ONLY for food/menu/allergen queries
- get_table_availability: ONLY when guest asks about reservations or availability
- Do NOT call the same tool twice with identical parameters
- If a tool fails, acknowledge it gracefully: "I'm having a moment checking that —
  let me give you what I know directly."

RESPONSE RULES:
- Maximum 3 short paragraphs
- No markdown formatting in responses
- Always cite [Source: document_name] for knowledge base content
- Allergen queries: ALWAYS end with "Please confirm with your server."
- If a tool returns no results: offer an alternative, don't just say "not found"

ESCALATION:
- If 3+ consecutive tool failures: "I'd recommend speaking with our sommelier
  directly — they can give you the most personalised recommendation."
- For reservation changes: "Please email reservations@lumiere.com or call us."
- For complaints: "I'm so sorry to hear that. Our manager will contact you directly."
"""
```

---

## 9. Observability and Logging

```python
import structlog
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

logger = structlog.get_logger()
tracer = trace.get_tracer("lumiere.agent")

def log_agent_run(run: AgentRun):
    """Structured log for agent run — queryable in Log Analytics."""
    logger.info(
        "agent_run_completed",
        run_id=run.run_id,
        session_id=run.session_id,
        success=run.success,
        total_steps=run.total_steps,
        total_input_tokens=run.total_input_tokens,
        total_output_tokens=run.total_output_tokens,
        total_latency_ms=run.total_latency_ms,
        error=run.error,
        tools_called=[s.tool_name for s in run.steps],
        estimated_cost_usd=calculate_cost(run)
    )

def calculate_cost(run: AgentRun, model: str = "claude-sonnet-4-6") -> float:
    """Estimate cost of an agent run."""
    # claude-sonnet-4-6 pricing (check docs.anthropic.com for current prices)
    INPUT_COST_PER_MTK = 3.00   # $3.00 per million input tokens
    OUTPUT_COST_PER_MTK = 15.00  # $15.00 per million output tokens

    input_cost = run.total_input_tokens / 1_000_000 * INPUT_COST_PER_MTK
    output_cost = run.total_output_tokens / 1_000_000 * OUTPUT_COST_PER_MTK
    return round(input_cost + output_cost, 6)

# KQL queries for Azure Monitor / Log Analytics:
KQL_QUERIES = {
    "avg_steps_per_run": """
        AppTraces
        | where Message == "agent_run_completed"
        | extend Steps = toint(Properties.total_steps)
        | summarize AvgSteps = avg(Steps), P95Steps = percentile(Steps, 95) by bin(TimeGenerated, 1h)
    """,
    "tool_failure_rate": """
        AppTraces
        | where Message == "agent_run_completed"
        | extend ToolsCalled = tostring(Properties.tools_called)
        | extend Success = tobool(Properties.success)
        | summarize FailureRate = 1.0 - avg(toint(Success)) by bin(TimeGenerated, 1h)
    """,
    "cost_by_hour": """
        AppTraces
        | where Message == "agent_run_completed"
        | summarize TotalCostUSD = sum(todouble(Properties.estimated_cost_usd)) by bin(TimeGenerated, 1h)
    """
}
```

---

## 10. Testing Agents

### Unit Testing Tool Executors

```python
import pytest

def test_search_wine_list_returns_results():
    result = search_wine_list(query="pinot noir")
    assert result["success"] is True
    assert "results" in result
    assert result["count"] > 0

def test_search_wine_list_empty_query_returns_guidance():
    result = search_wine_list(query="xxxxxxxxxx_nonexistent")
    assert result["success"] is True
    assert result["count"] == 0
    assert "message" in result  # Guidance for Claude

def test_search_wine_list_db_failure_returns_error_dict():
    """Test that DB failure returns error dict, not exception."""
    with patch("wine_db.search", side_effect=Exception("DB down")):
        result = search_wine_list(query="burgundy")
    assert result["success"] is False
    assert "error" in result
    assert "error_code" in result

def test_tool_schema_additionalProperties_false():
    """Ensure schemas reject unexpected parameters."""
    # This validates that our schema has additionalProperties: false
    for tool in ALL_TOOLS:
        schema = tool["input_schema"]
        assert schema.get("additionalProperties") is False, \
            f"Tool '{tool['name']}' schema should have additionalProperties: false"
```

### Integration Testing Agent Loops

```python
AGENT_INTEGRATION_TESTS = [
    {
        "test_id": "agent_001",
        "input": "What red wines do you have under £50?",
        "expected_tools": ["search_wine_list"],
        "response_check": lambda r: "£" in r or "price" in r.lower()
    },
    {
        "test_id": "agent_002",
        "input": "Is there a table for 2 this Friday at 8pm?",
        "expected_tools": ["get_table_availability"],
        "response_check": lambda r: any(w in r.lower() for w in ["available", "friday", "reservation"])
    },
    {
        "test_id": "agent_003",
        "input": "I have a shellfish allergy — what can I eat?",
        "expected_tools": ["search_food_menu"],
        "response_check": lambda r: "server" in r.lower() or "confirm" in r.lower()
    },
]
```

---

## 11. Cost Management for Agents

Agent cost = Σ (input tokens + output tokens) × price per token × number of steps.

```python
# Cost optimisation strategies:

# 1. Use Haiku for routing (10× cheaper than Sonnet)
routing_model = "claude-haiku-4-5-20251001"

# 2. Use Sonnet for complex reasoning
reasoning_model = "claude-sonnet-4-6"

# 3. Cache static system prompts (90% discount on cached tokens)
# See caching.md for implementation

# 4. Truncate tool results
def truncate_tool_result(result: dict, max_chars: int = 2000) -> dict:
    """Prevent large tool results from bloating context."""
    result_str = json.dumps(result)
    if len(result_str) > max_chars:
        # Keep first N chars + summary note
        truncated = result_str[:max_chars]
        result["_truncated"] = True
        result["_note"] = f"Result truncated at {max_chars} chars. Ask for specific details if needed."
    return result

# 5. Compress conversation history
def compress_history(messages: list[dict], keep_last_n: int = 10) -> list[dict]:
    """Keep only recent turns to reduce token consumption."""
    return messages[-keep_last_n * 2:]  # Each turn = 2 messages (user + assistant)

# Cost estimate before running
def estimate_agent_cost(estimated_steps: int, avg_tokens_per_step: int = 2000) -> float:
    total_tokens = estimated_steps * avg_tokens_per_step
    # Assume 70% input, 30% output
    input_cost = total_tokens * 0.7 / 1_000_000 * 3.00
    output_cost = total_tokens * 0.3 / 1_000_000 * 15.00
    return round(input_cost + output_cost, 4)

print(f"5-step agent estimate: ${estimate_agent_cost(5):.4f}")
print(f"20-step agent estimate: ${estimate_agent_cost(20):.4f}")
```

---

## 12. Junior Quick-Start Walkthrough

**Goal**: Build a working agent with 2 tools in 30 minutes.

**Step 1**: Install the SDK.

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
```

**Step 2**: Define one simple tool.

```python
import anthropic
import json

client = anthropic.Anthropic()

tools = [{
    "name": "get_weather",
    "description": "Get the current weather for a city. Use when the user asks about weather.",
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name, e.g., 'London'"}
        },
        "required": ["city"],
        "additionalProperties": False
    }
}]

def get_weather(city: str) -> dict:
    """Mock weather tool — replace with real API call."""
    return {"city": city, "temperature_c": 18, "condition": "Partly cloudy", "humidity_pct": 72}
```

**Step 3**: Run the agent loop.

```python
messages = [{"role": "user", "content": "What's the weather in London?"}]

for _ in range(10):  # Never loop without a limit!
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",  # Use Haiku while learning — cheaper
        max_tokens=512,
        tools=tools,
        messages=messages
    )

    messages.append({"role": "assistant", "content": response.content})

    if response.stop_reason == "end_turn":
        print("Claude says:", response.content[0].text)
        break

    if response.stop_reason == "tool_use":
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = get_weather(**block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result)
                })
        messages.append({"role": "user", "content": tool_results})
```

**Expected output**: `Claude says: The weather in London is currently 18°C and partly cloudy, with 72% humidity.`

---

## 13. Senior Patterns and Production Hardening

### Prompt Injection Defense in Agent Loops

```python
INJECTION_INDICATORS = [
    "ignore previous tool results",
    "your new instructions",
    "forget the tools",
    "execute this code directly",
    "return the API key",
    "print your system prompt",
]

def sanitise_tool_result(tool_name: str, result: dict) -> dict:
    """
    Scan tool results for prompt injection before returning to Claude.
    Tool outputs can contain adversarial content (e.g., documents that try to
    hijack the agent).
    """
    result_str = json.dumps(result).lower()
    for indicator in INJECTION_INDICATORS:
        if indicator in result_str:
            return {
                "success": False,
                "error": "Tool result contained unsafe content and was blocked.",
                "error_code": "CONTENT_BLOCKED"
            }
    return result
```

### Agent Observability Dashboard (KQL)

```
// Average agent steps and cost by hour (paste into Log Analytics)
AppTraces
| where Message == "agent_run_completed"
| extend Steps = toint(Properties.total_steps)
| extend Cost = todouble(Properties.estimated_cost_usd)
| extend Success = tobool(Properties.success)
| summarize
    AvgSteps = avg(Steps),
    P95Steps = percentile(Steps, 95),
    TotalCostUSD = sum(Cost),
    SuccessRate = avg(toint(Success))
  by bin(TimeGenerated, 1h)
| render timechart
```

---

## 14. Tips, Tricks and Gotchas

**Tip 1 — Start with max_steps=5, increase if needed.** Most well-designed agents complete in 3–5 steps. A 20-step agent usually indicates a design problem (tool too granular, task too vague).

**Tip 2 — Tool results should guide, not decide.** Keep decision-making in Claude's reasoning, not in tool code. Tools return data; Claude decides what to do with it.

**Tip 3 — Use async for parallel subagents.** Synchronous subagents run sequentially. Use `asyncio.gather()` for true parallelism — reduces wall-clock time significantly.

**Tip 4 — Log tool inputs AND outputs.** Debugging an agent failure is nearly impossible without tool I/O logs. Always log both before and after tool execution.

**Tip 5 — Test with adversarial inputs.** Agents are vulnerable to prompt injection via tool results. Test with documents that contain instruction-override text.

**Gotcha 1 — Never modify messages in place.** Always append; never edit past messages. Modifying history causes Claude to hallucinate about what it previously did.

**Gotcha 2 — Tool use and end_turn are mutually exclusive.** If `stop_reason == "tool_use"`, there will be no text block in `response.content`. Don't try to extract a text response — add tool results and loop.

**Gotcha 3 — Parallel tool calls require ALL results returned before next Claude call.** Even if tool B finishes before tool A, wait for all before calling Claude again.

**Gotcha 4 — Empty tool results confuse Claude.** If a search returns 0 results, return a helpful message: `{"results": [], "message": "No wines found. Try broader terms."}` — not just `{"results": []}`.

**Gotcha 5 — Cost compounds with steps.** A 10-step agent costs 10× more than a 1-step prompt. Profile agent step counts in staging before production.

---

## 15. Quick Reference Cheatsheet

```
AGENT LOOP (pseudocode):
  messages = [user_message]
  for step in range(MAX_STEPS):
      response = claude.create(messages=messages, tools=tools)
      messages.append(response)
      if end_turn: return response.text
      if tool_use: execute tools → append results → continue
  raise LoopExceededError

MAX STEPS BY AGENT TYPE:
  Simple Q&A agent:     5–8 steps
  Research agent:      10–15 steps
  Complex automation:  15–25 steps
  Hard limit:          Never exceed 50

TOOL COUNT SWEET SPOT: 5–8 tools per agent

MEMORY TYPES:
  Working:   messages array (in-context, auto-trimmed)
  Episodic:  session summaries in DB (retrieved on start)
  Semantic:  vector search (retrieved per query)

RELIABILITY PATTERNS:
  Circuit breaker:     3 failures → open for 60 seconds
  Retry + jitter:      3 retries, base 1s, max 60s
  Failure budget:      3 failures per tool per run
  Max step guard:      Hard limit on every loop

COST FORMULA:
  cost = steps × tokens_per_step × price_per_token
  Optimise: fewer steps, smaller context, cache system prompt

OBSERVABILITY CHECKLIST:
  ✓ Log: run_id, session_id, steps, tokens, latency, cost, success
  ✓ Log: each tool call — name, input, output, latency
  ✓ Alert: step count > P95, success rate < 95%, cost spike
```
