# tool-use.md — Claude Tool Use (Function Calling) Patterns

> **Purpose**: Complete guide to defining, calling, and handling tools in Claude for reliable agentic workflows — from basic function calling to advanced parallel execution and error handling.  
> **Owner**: jose@hybridgenai.com  
> **Updated**: 2026-05-22

---

## Navigation

1. [Tool Use Mechanics](#1-tool-use-mechanics)
2. [Complete Tool Schema Reference](#2-complete-tool-schema-reference)
3. [Tool Call Handling Loop](#3-tool-call-handling-loop)
4. [Tool Choice Control](#4-tool-choice-control)
5. [Schema Design Best Practices](#5-schema-design-best-practices)
6. [Error Handling in Tools](#6-error-handling-in-tools)
7. [Parallel Tool Calls](#7-parallel-tool-calls)
8. [Streaming with Tools](#8-streaming-with-tools)
9. [Tool Result Formatting](#9-tool-result-formatting)
10. [Tools as Structured Output](#10-tools-as-structured-output)
11. [Computer Use Tools](#11-computer-use-tools)
12. [Junior Quick-Start Walkthrough](#12-junior-quick-start-walkthrough)
13. [Senior Patterns and Production Hardening](#13-senior-patterns-and-production-hardening)
14. [Tips, Tricks and Gotchas](#14-tips-tricks-and-gotchas)
15. [Quick Reference Cheatsheet](#15-quick-reference-cheatsheet)

---

## 1. Tool Use Mechanics

Claude's tool use is a structured request/response protocol:

```
┌─────────────────────────────────────────────┐
│  1. YOU define tools (JSON schema) in API   │
│     request alongside messages              │
│           ↓                                  │
│  2. CLAUDE reasons → decides which tool     │
│     to call + constructs arguments          │
│           ↓                                  │
│  3. YOU receive response with               │
│     stop_reason == "tool_use"               │
│     and tool_use blocks in content          │
│           ↓                                  │
│  4. YOU execute the tool                    │
│           ↓                                  │
│  5. YOU return tool results in next message │
│           ↓                                  │
│  6. CLAUDE continues reasoning with         │
│     results in context                      │
│           ↓                                  │
│  Repeat until stop_reason == "end_turn"    │
└─────────────────────────────────────────────┘
```

**Important**: Claude never executes tools itself. It only decides to call them and constructs the arguments. YOUR code runs the tool. This keeps dangerous actions under human control.

---

## 2. Complete Tool Schema Reference

Every tool has three required fields: `name`, `description`, and `input_schema`.

```python
tool_schema = {
    # REQUIRED: Verb phrase, underscore_separated, lowercase
    # Examples: search_wine_list, create_reservation, get_order_status
    "name": "search_wine_list",

    # REQUIRED: When to use, what it returns, what NOT to use it for.
    # This is read by Claude as part of its reasoning — treat it like a prompt.
    "description": (
        "Search the restaurant's wine list by producer, grape variety, "
        "appellation, vintage, or style. "
        "Use for ANY wine-related guest query. "
        "Returns: producer, wine name, vintage, appellation, style, price (£). "
        "Do NOT use for food menu queries — use search_food_menu for that."
    ),

    # REQUIRED: JSON Schema describing the tool's parameters
    "input_schema": {
        "type": "object",   # Always "object" at the top level

        "properties": {

            # String parameter
            "query": {
                "type": "string",
                "description": "Search terms. Examples: 'Burgundy Pinot Noir', 'Château Margaux', '2018 vintage', 'full bodied red under £80'"
            },

            # Number parameter with range guidance
            "max_price_gbp": {
                "type": "number",
                "description": "Maximum bottle price in GBP. Only include if guest stated a budget. Range: 20–2000."
            },

            # Integer parameter
            "top_k": {
                "type": "integer",
                "description": "Number of results to return. Default: 5. Range: 1–20."
            },

            # Boolean parameter
            "include_by_glass": {
                "type": "boolean",
                "description": "If true, include wines available by the glass. Default: false."
            },

            # Enum (constrained string)
            "style": {
                "type": "string",
                "enum": ["light_red", "medium_red", "full_red", "light_white", "full_white", "sparkling", "rose", "dessert", "fortified"],
                "description": "Wine style. Only set if guest specified a preference."
            },

            # Array parameter
            "exclude_producers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of producer names to exclude from results. Usually empty."
            },

            # Nested object parameter
            "filters": {
                "type": "object",
                "properties": {
                    "vintage_year_min": {"type": "integer", "description": "Earliest vintage year. Example: 2015"},
                    "vintage_year_max": {"type": "integer", "description": "Latest vintage year. Example: 2022"},
                    "country": {"type": "string", "description": "Country of origin. Example: France, Italy, Spain"}
                },
                "description": "Optional advanced filters."
            }
        },

        # Required parameters — only params Claude MUST always provide
        "required": ["query"],

        # IMPORTANT: Set to False to prevent Claude from hallucinating parameters
        "additionalProperties": False
    }
}
```

---

## 3. Tool Call Handling Loop

### Basic Loop

```python
import anthropic
import json

client = anthropic.Anthropic()

def run_tool_loop(
    user_message: str,
    tools: list[dict],
    tool_executors: dict,   # {"tool_name": callable}
    system_prompt: str = "",
    model: str = "claude-sonnet-4-6",
    max_steps: int = 20
) -> str:
    """
    Execute a full tool use loop.

    Args:
        user_message: The initial user request
        tools: List of tool schema dicts
        tool_executors: Dict mapping tool names to Python callables
        system_prompt: Optional system prompt
        model: Claude model to use
        max_steps: Hard limit on loop iterations

    Returns:
        Final text response from Claude
    """
    messages = [{"role": "user", "content": user_message}]

    for step in range(max_steps):

        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            tools=tools,
            messages=messages,
        )

        # Always append Claude's response to history
        # IMPORTANT: Append the full response.content (list), not just text
        messages.append({"role": "assistant", "content": response.content})

        # ─── Termination ───────────────────────────────────────────────
        if response.stop_reason == "end_turn":
            # Extract text from final response
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""  # No text (shouldn't happen in normal end_turn)

        # ─── Max tokens hit ────────────────────────────────────────────
        if response.stop_reason == "max_tokens":
            # Claude was cut off mid-response — increase max_tokens or summarise context
            raise RuntimeError(
                f"Response truncated at step {step+1}. "
                f"Increase max_tokens or reduce context size."
            )

        # ─── Tool calls ────────────────────────────────────────────────
        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_name = block.name
                tool_input = block.input  # Already a Python dict — no need to parse
                tool_use_id = block.id   # Must be echoed in tool_result

                # Execute the tool
                executor = tool_executors.get(tool_name)
                if executor:
                    try:
                        result = executor(**tool_input)
                    except TypeError as e:
                        # Wrong parameter names — schema/executor mismatch
                        result = {"success": False, "error": f"Parameter error: {e}"}
                    except Exception as e:
                        result = {"success": False, "error": str(e)}
                else:
                    result = {"success": False, "error": f"Unknown tool: {tool_name}"}

                # Format result as tool_result message
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,   # Must match block.id exactly
                    "content": json.dumps(result), # Must be a string
                })

            # Return ALL tool results in a single user message
            messages.append({"role": "user", "content": tool_results})

    raise RuntimeError(f"Agent exceeded {max_steps} steps without completing.")
```

---

### Annotated Message Flow

Here is what `messages` looks like after a two-step tool exchange:

```python
# After user message:
messages = [
    {"role": "user", "content": "What red wines pair well with lamb?"}
]

# After Claude's first response (tool_use):
messages = [
    {"role": "user", "content": "What red wines pair well with lamb?"},
    {"role": "assistant", "content": [
        # Claude might include a text block before the tool call
        {"type": "text", "text": "Let me check our wine list for you."},
        # The actual tool call
        {"type": "tool_use", "id": "toolu_01ABC...", "name": "search_wine_list",
         "input": {"query": "red wine lamb pairing", "food_pairing": "lamb"}}
    ]}
]

# After tool result returned:
messages = [
    {"role": "user", "content": "What red wines pair well with lamb?"},
    {"role": "assistant", "content": [...]},
    {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "toolu_01ABC...",
         "content": '{"success": true, "results": [{"name": "Château Léoville-Barton", "vintage": 2018, ...}]}'}
    ]}
]

# After final Claude response (end_turn):
messages = [
    ...,
    {"role": "assistant", "content": [
        {"type": "text", "text": "I'd recommend the Château Léoville-Barton 2018..."}
    ]}
]
```

---

## 4. Tool Choice Control

Control whether and which tools Claude uses.

```python
# ── AUTO (default) ──────────────────────────────────────────────────────────
# Claude decides whether to call a tool based on the user's request.
# Recommended for most use cases.
tool_choice = {"type": "auto"}

# ── ANY ─────────────────────────────────────────────────────────────────────
# Force Claude to call at least one tool. Useful for extraction/classification
# tasks where you always want structured output via a tool.
tool_choice = {"type": "any"}

# ── SPECIFIC TOOL ───────────────────────────────────────────────────────────
# Force Claude to call a specific named tool. Useful for structured extraction
# where you know exactly which schema you want populated.
tool_choice = {"type": "tool", "name": "extract_reservation_details"}

# ── NONE ────────────────────────────────────────────────────────────────────
# Disable tool use entirely for this turn. Useful for generating a
# conversational summary after all tools have been called.
tool_choice = {"type": "none"}

# Example: Force structured extraction
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=512,
    tools=[EXTRACT_RESERVATION_TOOL],
    tool_choice={"type": "tool", "name": "extract_reservation_details"},
    messages=[{
        "role": "user",
        "content": "I'd like a table for 4 on Saturday May 30th at 8pm, name John Smith."
    }]
)
# Response will always contain a tool_use block for extract_reservation_details
extraction = response.content[0].input
print(extraction)
# {"guest_name": "John Smith", "date": "2026-05-30", "time": "20:00", "party_size": 4}
```

---

## 5. Schema Design Best Practices

### Rule 1: Rich Descriptions Reduce Errors by 20–35%

```python
# ❌ Ambiguous — Claude might confuse with other search tools
{
    "name": "search",
    "description": "Search for information",
    "input_schema": {
        "type": "object",
        "properties": {"q": {"type": "string"}},
        "required": ["q"]
    }
}

# ✅ Precise — Claude knows exactly when, why, and how to use this
{
    "name": "search_food_menu",
    "description": (
        "Search the Lumière food menu for dish names, ingredients, descriptions, "
        "and allergen information. Use for any food-related guest query. "
        "Returns: dish name, description, course (starter/main/dessert), "
        "price, and allergen flags. "
        "Do NOT use for wine — use search_wine_list for wine queries."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Dish name, ingredient, or dietary requirement. "
                    "Examples: 'beef wellington', 'vegetarian main', "
                    "'gluten free', 'halibut'"
                )
            },
            "course": {
                "type": "string",
                "enum": ["starter", "main", "dessert", "cheese", "all"],
                "description": "Filter by course. Default: 'all'."
            },
            "dietary": {
                "type": "string",
                "enum": ["vegetarian", "vegan", "gluten_free", "dairy_free", "nut_free", "any"],
                "description": "Filter by dietary requirement. Default: 'any'."
            }
        },
        "required": ["query"],
        "additionalProperties": False
    }
}
```

### Rule 2: Use Enums for All Constrained Values

Enums prevent Claude from hallucinating invalid parameter values.

```python
# ❌ No enum — Claude might pass "Fish" or "FISH" or "seafood"
"course": {"type": "string", "description": "The course type"}

# ✅ With enum — Claude can only pass valid values
"course": {
    "type": "string",
    "enum": ["starter", "main", "dessert", "cheese"],
    "description": "Course type. Omit to search all courses."
}
```

### Rule 3: Always Set additionalProperties: False

```python
# Without this, Claude can hallucinate extra parameters that don't exist
"input_schema": {
    "type": "object",
    "properties": { ... },
    "required": [...],
    "additionalProperties": False   # ← This line prevents hallucinated params
}
```

### Rule 4: Describe When NOT to Use the Tool

```python
# In description field, always add what the tool does NOT do:
"description": (
    "Get current table availability. Use ONLY when guest asks about booking "
    "a table or checking availability. "
    "Do NOT use for menu queries — use search_food_menu instead. "
    "Do NOT use for past reservation lookups — use get_reservation_history."
)
```

### Rule 5: Example Values in Descriptions

```python
"date": {
    "type": "string",
    "description": "Date in YYYY-MM-DD format. Examples: '2026-06-15', '2026-12-31'."
},
"time": {
    "type": "string",
    "description": "Time in HH:MM 24-hour format. Examples: '19:00', '20:30', '12:00'."
},
"email": {
    "type": "string",
    "description": "Guest email address. Example: 'john.smith@email.com'."
}
```

---

## 6. Error Handling in Tools

Never throw exceptions from tool executors. Always return a structured response.

```python
from typing import Any

def tool_result_success(data: Any, message: str = "") -> dict:
    """Standard success response envelope."""
    result = {"success": True, "data": data}
    if message:
        result["message"] = message
    return result

def tool_result_error(
    error: str,
    error_code: str = "UNKNOWN",
    suggestion: str = ""
) -> dict:
    """Standard error response envelope."""
    result = {
        "success": False,
        "error": error,
        "error_code": error_code
    }
    if suggestion:
        result["suggestion"] = suggestion
    return result

# Complete tool with proper error handling:
def search_wine_list(
    query: str,
    max_price_gbp: float = None,
    style: str = None,
    top_k: int = 5
) -> dict:
    """
    Search wine list with full error handling.

    Error codes:
        EMPTY_RESULTS:   Query succeeded but no matching wines
        DB_TIMEOUT:      Database timed out
        DB_CONNECTION:   Cannot reach database
        INVALID_QUERY:   Query parameter invalid
        UNKNOWN:         Unexpected error
    """
    # Input validation
    if not query or not query.strip():
        return tool_result_error(
            "Query cannot be empty",
            error_code="INVALID_QUERY",
            suggestion="Provide a search term like 'Burgundy', 'Pinot Noir', or a producer name."
        )

    if max_price_gbp is not None and max_price_gbp <= 0:
        return tool_result_error(
            "max_price_gbp must be a positive number",
            error_code="INVALID_QUERY"
        )

    try:
        results = wine_db.search(
            query=query.strip(),
            max_price=max_price_gbp,
            style=style,
            limit=min(top_k, 20)  # Cap at 20 to avoid huge results
        )

        if not results:
            return {
                "success": True,
                "data": [],
                "count": 0,
                "message": (
                    f"No wines found matching '{query}'"
                    + (f" under £{max_price_gbp}" if max_price_gbp else "")
                    + ". Consider broadening the search or removing filters."
                ),
                "suggestions": [
                    "Try a broader term like 'red wine' instead of a specific producer",
                    "Remove the price filter to see all options",
                    "Ask the sommelier directly for personalised recommendations"
                ]
            }

        return {
            "success": True,
            "data": results,
            "count": len(results),
            "query_used": query
        }

    except TimeoutError:
        return tool_result_error(
            "Wine list database timed out after 5 seconds",
            error_code="DB_TIMEOUT",
            suggestion="Please try again in a moment, or ask a sommelier directly."
        )

    except ConnectionError:
        return tool_result_error(
            "Cannot connect to wine list database",
            error_code="DB_CONNECTION",
            suggestion="Our wine list system is temporarily unavailable. Please ask a sommelier."
        )

    except Exception as e:
        logger.error(f"search_wine_list unexpected error: {e}", exc_info=True)
        return tool_result_error(
            "Unexpected error during wine search",
            error_code="UNKNOWN"
        )
```

---

## 7. Parallel Tool Calls

Claude can call multiple tools in a single turn. Handle them all concurrently for performance.

### What Parallel Tool Use Looks Like

```python
# When Claude calls multiple tools in one turn, response.content contains
# multiple tool_use blocks:

# response.content might be:
[
    {"type": "text", "text": "Let me check both the menu and availability."},
    {"type": "tool_use", "id": "toolu_01", "name": "search_food_menu",
     "input": {"query": "vegetarian options"}},
    {"type": "tool_use", "id": "toolu_02", "name": "get_table_availability",
     "input": {"date": "2026-06-15", "time": "19:00", "party_size": 3}}
]
```

### Sequential Execution (Simple but Slower)

```python
# Execute tools one at a time — simpler but slow
tool_results = []
for block in response.content:
    if block.type == "tool_use":
        result = execute_tool(block.name, block.input)
        tool_results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": json.dumps(result)
        })
```

### Concurrent Execution (Recommended for Production)

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def execute_tool(tool_name: str, tool_input: dict, tool_executors: dict) -> tuple[str, dict]:
    """Execute a single tool and return (tool_use_id, result). Thread-safe."""
    executor = tool_executors.get(tool_name)
    try:
        result = executor(**tool_input) if executor else {"success": False, "error": f"Unknown: {tool_name}"}
    except Exception as e:
        result = {"success": False, "error": str(e)}
    return result

def execute_tools_parallel(
    tool_use_blocks: list,
    tool_executors: dict,
    timeout_seconds: float = 10.0
) -> list[dict]:
    """
    Execute multiple tool calls in parallel using ThreadPoolExecutor.
    Results are returned in the SAME ORDER as input blocks, regardless of
    completion order.

    Args:
        tool_use_blocks: List of tool_use content blocks from Claude response
        tool_executors: Dict mapping tool names to callables
        timeout_seconds: Max wait time for all tools

    Returns:
        List of tool_result dicts ready to append to messages
    """
    results_by_id = {}

    with ThreadPoolExecutor(max_workers=len(tool_use_blocks)) as pool:
        futures = {
            pool.submit(execute_tool, block.name, block.input, tool_executors): block.id
            for block in tool_use_blocks
            if block.type == "tool_use"
        }

        for future in as_completed(futures, timeout=timeout_seconds):
            tool_use_id = futures[future]
            try:
                result = future.result()
            except Exception as e:
                result = {"success": False, "error": str(e)}
            results_by_id[tool_use_id] = result

    # Return in original order (important for message consistency)
    tool_results = []
    for block in tool_use_blocks:
        if block.type == "tool_use" and block.id in results_by_id:
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(results_by_id[block.id])
            })

    return tool_results

# Usage in agent loop:
if response.stop_reason == "tool_use":
    tool_blocks = [b for b in response.content if b.type == "tool_use"]

    # Parallel execution — all tools run simultaneously
    tool_results = execute_tools_parallel(tool_blocks, TOOL_EXECUTORS, timeout_seconds=10.0)
    messages.append({"role": "user", "content": tool_results})
```

---

## 8. Streaming with Tools

When streaming, tool use blocks are emitted incrementally. Buffer them properly.

```python
def stream_with_tools(
    user_message: str,
    tools: list[dict],
    tool_executors: dict,
    on_text: callable = print  # Callback for streaming text to user
):
    """
    Stream Claude's response, handle tool calls when they complete.
    Text is streamed in real-time; tool execution happens at block boundaries.
    """
    messages = [{"role": "user", "content": user_message}]

    while True:
        current_tool_use = {}
        accumulated_content = []

        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            tools=tools,
            messages=messages,
        ) as stream:

            for event in stream:
                if event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        current_tool_use = {
                            "id": event.content_block.id,
                            "name": event.content_block.name,
                            "input_str": ""
                        }

                elif event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        # Stream text to user in real-time
                        on_text(event.delta.text, end="", flush=True)

                    elif event.delta.type == "input_json_delta":
                        # Accumulate JSON input for tool call
                        current_tool_use["input_str"] += event.delta.partial_json

                elif event.type == "content_block_stop":
                    if current_tool_use.get("id"):
                        # Tool use block complete — parse and store
                        tool_use = {
                            "type": "tool_use",
                            "id": current_tool_use["id"],
                            "name": current_tool_use["name"],
                            "input": json.loads(current_tool_use["input_str"])
                        }
                        accumulated_content.append(tool_use)
                        current_tool_use = {}

                elif event.type == "message_stop":
                    final_message = stream.get_final_message()
                    messages.append({"role": "assistant", "content": final_message.content})

                    if final_message.stop_reason == "end_turn":
                        on_text("\n")  # Final newline
                        return

                    if final_message.stop_reason == "tool_use":
                        # Execute tools (notify user briefly)
                        on_text("\n[Looking that up for you...]\n")

                        tool_results = []
                        for block in final_message.content:
                            if block.type == "tool_use":
                                executor = tool_executors.get(block.name)
                                result = executor(**block.input) if executor else {"error": "Unknown tool"}
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": json.dumps(result)
                                })

                        messages.append({"role": "user", "content": tool_results})
                        break  # Continue outer while loop
```

---

## 9. Tool Result Formatting

Tool results affect how well Claude reasons. Format them to be informative.

```python
# ❌ Poor result — minimal info, Claude can't reason well
{"wines": ["Château A", "Château B"]}

# ✅ Rich result — all fields Claude needs to give a good response
{
    "success": True,
    "count": 2,
    "query": "full bodied red lamb",
    "results": [
        {
            "name": "Château Léoville-Barton",
            "vintage": 2018,
            "appellation": "Saint-Julien, Bordeaux, France",
            "style": "full_red",
            "description": "Structured tannins, cassis, cedar. Classic Médoc profile.",
            "price_glass_gbp": None,
            "price_bottle_gbp": 145.0,
            "availability": "in_stock",
            "pairing_notes": "Exceptional with aged beef, lamb, and hard aged cheeses.",
            "source": "wine_list_2026.pdf",
            "page": 8
        },
        {
            "name": "Barolo Serralunga d'Alba",
            "vintage": 2019,
            "appellation": "Barolo DOCG, Piedmont, Italy",
            "style": "full_red",
            "description": "Tar, roses, cherries. High tannin, high acid. Needs decanting.",
            "price_glass_gbp": 28.0,
            "price_bottle_gbp": 95.0,
            "availability": "in_stock",
            "pairing_notes": "Outstanding with lamb, venison, and truffle dishes.",
            "source": "wine_list_2026.pdf",
            "page": 12
        }
    ]
}
```

### Truncating Large Results

```python
MAX_RESULT_CHARS = 3000  # ~750 tokens — keep tool results compact

def format_tool_result(result: dict, max_chars: int = MAX_RESULT_CHARS) -> str:
    """
    Serialise tool result to string, truncating if too large.
    Large tool results bloat context and increase cost.
    """
    result_str = json.dumps(result, default=str)

    if len(result_str) <= max_chars:
        return result_str

    # Truncate but preserve structure
    truncated_result = {
        "success": result.get("success", True),
        "count": result.get("count", "?"),
        "_truncated": True,
        "_message": f"Result truncated to {max_chars} chars. Ask for specific items by name for full details.",
        "data_preview": result_str[:max_chars - 200]
    }
    return json.dumps(truncated_result)
```

---

## 10. Tools as Structured Output

The most reliable way to get structured output from Claude is to define a "schema tool" and force its use. Claude MUST populate all required fields correctly.

```python
# Define a tool purely as a structured output schema
EXTRACT_RESERVATION_TOOL = {
    "name": "extract_reservation_details",
    "description": "Extract reservation details from the guest's message into structured format.",
    "input_schema": {
        "type": "object",
        "properties": {
            "guest_name": {
                "type": "string",
                "description": "Guest's full name. Null if not provided."
            },
            "party_size": {
                "type": "integer",
                "description": "Number of guests (1–20). Null if not mentioned."
            },
            "date": {
                "type": "string",
                "description": "Date in YYYY-MM-DD. Null if not mentioned. Today is 2026-05-22."
            },
            "time": {
                "type": "string",
                "description": "Time in HH:MM 24-hour format. Null if not mentioned."
            },
            "special_requests": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of special requests (dietary, anniversary, etc.)"
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": "Confidence that all required fields were correctly extracted."
            }
        },
        "required": ["guest_name", "party_size", "date", "time", "special_requests", "confidence"],
        "additionalProperties": False
    }
}

def extract_reservation(guest_message: str) -> dict:
    """Extract reservation details from natural language."""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        tools=[EXTRACT_RESERVATION_TOOL],
        # Force Claude to always use this tool
        tool_choice={"type": "tool", "name": "extract_reservation_details"},
        messages=[{
            "role": "user",
            "content": guest_message
        }]
    )

    # With forced tool_choice, response.content[0] is always a tool_use block
    for block in response.content:
        if block.type == "tool_use":
            return block.input

    return {}  # Fallback (shouldn't occur with forced tool_choice)

# Example
result = extract_reservation(
    "I'd like to book a table for my anniversary dinner — party of 2, "
    "next Friday evening around 8. Name is Sarah Johnson. We'll need a "
    "vegetarian option for my partner."
)
print(result)
# {
#   "guest_name": "Sarah Johnson",
#   "party_size": 2,
#   "date": "2026-05-29",
#   "time": "20:00",
#   "special_requests": ["anniversary dinner", "vegetarian option required"],
#   "confidence": "high"
# }
```

---

## 11. Computer Use Tools

Claude can control a computer via special tools. These require explicit permission and careful design.

```python
# Computer use tools follow the same schema but have special names:
COMPUTER_USE_TOOLS = [
    {
        "type": "computer_20241022",
        "name": "computer",
        "display_width_px": 1280,
        "display_height_px": 800,
        "display_number": 1
    },
    {
        "type": "text_editor_20241022",
        "name": "str_replace_editor"
    },
    {
        "type": "bash_20241022",
        "name": "bash"
    }
]

# Always add safety rules for computer use agents:
COMPUTER_USE_SYSTEM = """
You have access to a computer. Use it carefully.

SAFETY RULES:
1. Never execute commands that delete files without explicit user confirmation.
2. Never send emails or messages without showing the user the content first.
3. Never submit forms containing financial or personal data without review.
4. If a step seems irreversible, pause and confirm with the user.
5. Prefer reading to writing; prefer reversible to irreversible actions.
"""
```

---

## 12. Junior Quick-Start Walkthrough

**Goal**: Make your first tool call in 10 minutes.

**Step 1**: Create one simple tool.

```python
import anthropic, json

client = anthropic.Anthropic()

tools = [{
    "name": "calculate_tip",
    "description": "Calculate a tip amount given a bill total and tip percentage.",
    "input_schema": {
        "type": "object",
        "properties": {
            "bill_total": {"type": "number", "description": "Total bill amount in pounds"},
            "tip_percentage": {"type": "number", "description": "Tip percentage (e.g., 10, 15, 20)"}
        },
        "required": ["bill_total", "tip_percentage"],
        "additionalProperties": False
    }
}]
```

**Step 2**: Create the executor function.

```python
def calculate_tip(bill_total: float, tip_percentage: float) -> dict:
    tip_amount = bill_total * tip_percentage / 100
    total = bill_total + tip_amount
    return {
        "bill_total": bill_total,
        "tip_percentage": tip_percentage,
        "tip_amount": round(tip_amount, 2),
        "grand_total": round(total, 2)
    }
```

**Step 3**: Call Claude and handle the tool use.

```python
messages = [{"role": "user", "content": "My bill is £85.40. What's a 15% tip?"}]

response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=256,
    tools=tools,
    messages=messages
)

# Handle tool use
if response.stop_reason == "tool_use":
    messages.append({"role": "assistant", "content": response.content})

    tool_results = []
    for block in response.content:
        if block.type == "tool_use":
            result = calculate_tip(**block.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result)
            })

    messages.append({"role": "user", "content": tool_results})

    # Get final response
    final = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        tools=tools,
        messages=messages
    )
    print(final.content[0].text)
    # "A 15% tip on £85.40 would be £12.81, bringing your total to £98.21."
```

---

## 13. Senior Patterns and Production Hardening

### Tool Input Validation Before Execution

```python
from jsonschema import validate, ValidationError

def validate_and_execute(
    tool_name: str,
    tool_input: dict,
    tool_schemas: dict[str, dict],
    tool_executors: dict[str, callable]
) -> dict:
    """
    Validate tool input against schema before execution.
    Catches Claude hallucinating invalid parameter types.
    """
    schema = tool_schemas.get(tool_name, {}).get("input_schema", {})

    try:
        validate(instance=tool_input, schema=schema)
    except ValidationError as e:
        return {
            "success": False,
            "error": f"Invalid tool input: {e.message}",
            "error_code": "SCHEMA_VALIDATION_FAILED",
            "path": list(e.absolute_path)
        }

    executor = tool_executors.get(tool_name)
    if not executor:
        return {"success": False, "error": f"Unknown tool: {tool_name}", "error_code": "UNKNOWN_TOOL"}

    return executor(**tool_input)
```

### Tool Call Audit Log

```python
import time

def audited_tool_call(
    tool_name: str,
    tool_input: dict,
    tool_use_id: str,
    executor: callable,
    session_id: str = ""
) -> dict:
    """Execute tool with full audit logging."""
    start = time.time()

    try:
        result = executor(**tool_input)
        success = result.get("success", True)
        error = result.get("error") if not success else None
    except Exception as e:
        result = {"success": False, "error": str(e)}
        success = False
        error = str(e)

    latency_ms = (time.time() - start) * 1000

    audit_logger.info(
        "tool_called",
        tool_name=tool_name,
        tool_use_id=tool_use_id,
        session_id=session_id,
        input_keys=list(tool_input.keys()),
        success=success,
        error=error,
        latency_ms=round(latency_ms, 2)
    )

    return result
```

---

## 14. Tips, Tricks and Gotchas

**Tip 1 — Use `tool_choice: "tool"` for structured extraction.** This is the most reliable way to extract structured data — more reliable than asking Claude to return JSON in text.

**Tip 2 — Keep tool results under 1,000 tokens (~4,000 chars).** Large tool results bloat the context rapidly, especially in multi-step agents. Summarise or truncate before returning.

**Tip 3 — Tool descriptions are more important than parameter descriptions.** Claude reads the tool description first to decide whether to call it. A perfect schema with a vague description = wrong tool selection.

**Tip 4 — Test tool schemas with edge cases.** Check what Claude does when given ambiguous input: "Some wine" (too vague), "I want a £20,000 bottle" (unusual), "Tell me all wines" (no filter). The tool description should handle these gracefully.

**Tip 5 — Parallel tool calls reduce latency significantly.** If Claude calls 3 tools that each take 200ms, sequential = 600ms, parallel = ~200ms.

**Gotcha 1 — `tool_use_id` must exactly match `block.id`.** If you return a tool_result with the wrong ID, the API returns a 400 error. Always use `block.id`, never generate your own.

**Gotcha 2 — Tool results must be strings.** The `content` field of a `tool_result` must be a string (usually `json.dumps(result)`), not a dict. Passing a dict directly causes an API error.

**Gotcha 3 — Claude can call zero tools even with `tool_choice: "auto"`.** If Claude decides the user's query doesn't require a tool, it answers directly. This is correct behaviour — design tool descriptions accordingly.

**Gotcha 4 — Don't pass tools on the follow-up call unless needed.** After tool results are returned, you still need to include `tools` in the API call (Claude may call more tools). But if you're using `tool_choice: "none"` for a summary, you can omit tools.

**Gotcha 5 — Tool timeouts must be handled externally.** Claude's timeout doesn't know about your tool execution time. Set your own timeout in the executor and return an error dict — never let a slow tool block the agent loop indefinitely.

---

## 15. Quick Reference Cheatsheet

```
TOOL SCHEMA REQUIRED FIELDS:
  name:          Verb phrase, underscore_separated ("search_wine_list")
  description:   When to use + what it returns + what NOT to use it for
  input_schema:  JSON Schema object with properties, required, additionalProperties: false

PARAMETER TYPES:
  string         → Free text, with enum for constrained values
  number         → Float (price, percentage, coordinates)
  integer        → Whole number (count, year, party size)
  boolean        → True/false flag
  array          → List of items (items type required)
  object         → Nested object (properties required)

TOOL CHOICE OPTIONS:
  auto           → Claude decides (default, recommended)
  any            → Must call at least one tool
  {"type":"tool","name":"X"} → Must call tool X (best for extraction)
  none           → No tool calls this turn

TOOL RESULT FORMAT:
  {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)}
  content must be a STRING, not a dict

STOP REASONS:
  end_turn      → Final answer ready (extract text from content)
  tool_use      → Execute tools, append results, loop again
  max_tokens    → Truncated — increase max_tokens
  stop_sequence → Triggered stop sequence

ERROR RESULT PATTERN:
  {"success": False, "error": "message", "error_code": "CODE", "suggestion": "..."}

PARALLEL EXECUTION:
  Use ThreadPoolExecutor for sync tools
  Use asyncio.gather() for async tools
  Always collect ALL results before sending next message

STRUCTURED OUTPUT:
  Define schema as a tool + tool_choice: {"type":"tool","name":"X"}
  Claude MUST return populated schema — most reliable structured output method
```
