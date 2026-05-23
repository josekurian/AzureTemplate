# streaming.md — Streaming Responses from Claude

> **Purpose**: Complete guide to implementing, optimizing, and handling streaming for real-time Claude outputs. Covers synchronous streaming, async streaming, SSE endpoints, WebSocket, tool use with streaming, partial response handling, and production patterns.
> **Who This Is For**: Junior developers building first streaming integration; senior engineers building production streaming infrastructure.
> **Owner**: jose@hybridgenai.com

---

## Navigation

1. [Why Stream?](#1-why-stream)
2. [Streaming Event Architecture](#2-streaming-event-architecture)
3. [Basic Streaming — Synchronous](#3-basic-streaming--synchronous)
4. [Async Streaming (FastAPI / ASGI Apps)](#4-async-streaming-fastapi--asgi-apps)
5. [Streaming with Tool Use](#5-streaming-with-tool-use)
6. [Streaming Event Types Reference](#6-streaming-event-types-reference)
7. [Frontend Integration Patterns](#7-frontend-integration-patterns)
8. [Partial Response Handling](#8-partial-response-handling)
9. [Error Handling in Streams](#9-error-handling-in-streams)
10. [Advanced: Structured Output via Streaming](#10-advanced-structured-output-via-streaming)
11. [Performance Considerations](#11-performance-considerations)
12. [Junior Walkthrough — Add Streaming to Existing App](#12-junior-walkthrough--add-streaming-to-existing-app)
13. [Senior Patterns — Production SSE Infrastructure](#13-senior-patterns--production-streaming-infrastructure)
14. [Tips, Tricks, and Gotchas](#14-tips-tricks-and-gotchas)
15. [Quick Reference Cheatsheet](#15-quick-reference-cheatsheet)

---

## 1. Why Stream?

### The Numbers

```
Scenario: Claude generates a 500-token response (typical chat reply)
         at 100 tokens/second.

Without streaming:
  0ms    ──── user waits ────────────────────────────── 5,000ms
                                                         ↑ User sees text

With streaming:
  0ms ── 600ms (TTFT) ── user reads first words ───── 5,600ms
               ↑                     ↑
          First token           Continued reading
          arrives               while generation continues

UX improvement:
  Perceived wait:   5,000ms → 600ms (88% reduction)
  Total wait:       5,000ms → 5,600ms (total is slightly LONGER due to streaming overhead)
  User satisfaction: significantly higher (user is reading, not staring at spinner)
```

### When Streaming Matters Most

```python
# High value: Long responses the user will read
# Low value:  Short machine-consumed results

STREAM_DECISIONS = {
    "chat_response":            True,   # User reads it — always stream
    "wine_recommendation":      True,   # 200-400 tokens — user reads
    "document_analysis":        True,   # Long — especially valuable
    "classification_result":    False,  # 5 tokens — not worth the overhead
    "json_extraction":          False,  # Machine-consumed — no UX benefit
    "batch_processing":         False,  # No human watching
    "agent_final_response":     True,   # User is waiting for it
    "agent_tool_thoughts":      True,   # Show progress to user
}
```

---

## 2. Streaming Event Architecture

Understanding the event types prevents bugs when integrating with tool use.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CLAUDE STREAMING EVENT FLOW                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  message_start          ← Message metadata (ID, model, initial usage)│
│  │                                                                    │
│  ├── content_block_start (index=0, type="text")                      │
│  │       ├── content_block_delta (delta.type="text_delta")  × many   │
│  │       ├── content_block_delta (delta.type="text_delta")           │
│  │       └── content_block_stop                                       │
│  │                                                                    │
│  ├── content_block_start (index=1, type="tool_use")  ← if tool used  │
│  │       ├── content_block_delta (delta.type="input_json_delta") × N │
│  │       └── content_block_stop                                       │
│  │                                                                    │
│  └── message_delta (stop_reason, final usage)                        │
│  message_stop                                                         │
│                                                                       │
│  stream.get_final_message() ← Assembled full Message object          │
└─────────────────────────────────────────────────────────────────────┘

Key insight:
  - stream.text_stream        → yields only text_delta content (simple)
  - Iterating over stream     → yields ALL events (full control)
  - stream.get_final_message()→ assembled message with full usage stats
```

---

## 3. Basic Streaming — Synchronous

### 3.1 Simplest Form (text_stream)

```python
import anthropic
import os

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

def stream_to_console(question: str) -> str:
    """
    Stream Claude's response to the console in real-time.
    
    Returns the complete text when done.
    
    Args:
        question: The user's question
    
    Returns:
        Complete response as a string
    
    Usage:
        response = stream_to_console("What wines pair with duck confit?")
    """
    full_text = ""
    
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="You are Maître, concierge AI for Lumière restaurant in London.",
        messages=[{"role": "user", "content": question}],
    ) as stream:
        
        # text_stream yields only the text content — simplest way to stream
        for text in stream.text_stream:
            print(text, end="", flush=True)  # flush=True: write immediately, no buffer
            full_text += text
        
        # ALWAYS capture the final message for token usage monitoring
        final = stream.get_final_message()
        
        print(f"\n\n─── Usage ───")
        print(f"Input:  {final.usage.input_tokens} tokens")
        print(f"Output: {final.usage.output_tokens} tokens")
        print(f"Cost:   ${(final.usage.input_tokens * 0.000003) + (final.usage.output_tokens * 0.000015):.4f}")
    
    return full_text

# Run it
text = stream_to_console("Recommend a wine under £60 for the beef tartare starter.")
```

### 3.2 Streaming with System Prompt and Multi-Turn History

```python
def stream_multi_turn(
    messages: list[dict],
    system: str,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 1024,
) -> tuple[str, anthropic.types.Message]:
    """
    Stream a response in a multi-turn conversation.
    
    Args:
        messages:   Full conversation history (user/assistant turns)
        system:     System prompt
        model:      Which Claude model to use
        max_tokens: Maximum output tokens
    
    Returns:
        (response_text, final_message)
        Add response_text to messages as {"role": "assistant", "content": response_text}
        
    Example:
        messages = [{"role": "user", "content": "Tell me about your tasting menu."}]
        text, final = stream_multi_turn(messages, SYSTEM_PROMPT)
        messages.append({"role": "assistant", "content": text})
        
        # Continue conversation
        messages.append({"role": "user", "content": "What wine pairs with it?"})
        text2, final2 = stream_multi_turn(messages, SYSTEM_PROMPT)
    """
    full_text = ""
    
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_text += text
        
        final = stream.get_final_message()
    
    return full_text, final
```

---

## 4. Async Streaming (FastAPI / ASGI Apps)

### 4.1 Server-Sent Events (SSE) Endpoint

```python
import asyncio
import json
import anthropic
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

logger = logging.getLogger(__name__)

client_async = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
app = FastAPI(title="Lumière Chat API")

# Allow browser connections from your frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://lumiere-restaurant.co.uk", "http://localhost:3000"],
    allow_methods=["GET"],
)

LUMIERE_SYSTEM = """You are Maître, the AI concierge for Lumière restaurant.
Be warm, knowledgeable, and concise. Focus exclusively on restaurant topics.
Allergen queries: always end with "Please confirm with your server before ordering."
"""

@app.get("/api/chat/stream")
async def stream_chat_sse(
    question: str = Query(..., min_length=1, max_length=1000),
    session_id: str = Query(default=""),
):
    """
    Stream Claude's response using Server-Sent Events.
    
    Frontend usage:
        const es = new EventSource('/api/chat/stream?question=' + encodeURIComponent(q))
        es.onmessage = (e) => {
            const data = JSON.parse(e.data)
            if (data.done) { es.close(); return; }
            appendText(data.text)
        }
    
    SSE Event format:
        data: {"text": "The wine", "done": false}\n\n
        data: {"text": " list features", "done": false}\n\n
        ...
        data: {"done": true, "usage": {"input": 150, "output": 320}}\n\n
        data: [DONE]\n\n
    """
    
    async def generate():
        try:
            # Build request with optional session context
            messages = await build_messages_for_session(session_id, question)
            
            async with client_async.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=800,
                system=LUMIERE_SYSTEM,
                messages=messages,
            ) as stream:
                
                async for text in stream.text_stream:
                    # SSE format REQUIRES double newline to flush each event
                    event_data = json.dumps({"text": text, "done": False})
                    yield f"data: {event_data}\n\n"
                
                # Capture final message
                final = await stream.get_final_message()
                
                # Send done signal with usage info
                done_data = json.dumps({
                    "done": True,
                    "usage": {
                        "input_tokens": final.usage.input_tokens,
                        "output_tokens": final.usage.output_tokens,
                    }
                })
                yield f"data: {done_data}\n\n"
                yield "data: [DONE]\n\n"
                
                # Log for cost monitoring
                logger.info(f"Stream complete: {final.usage.input_tokens}→{final.usage.output_tokens} tokens")
        
        except anthropic.RateLimitError:
            error_data = json.dumps({"error": "Service is busy. Please try again in a moment.", "done": True})
            yield f"data: {error_data}\n\n"
        
        except anthropic.BadRequestError as e:
            error_data = json.dumps({"error": "Invalid request. Please rephrase your question.", "done": True})
            yield f"data: {error_data}\n\n"
        
        except Exception as e:
            logger.exception(f"Unexpected error in stream: {e}")
            error_data = json.dumps({"error": "An unexpected error occurred.", "done": True})
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",          # Don't cache SSE streams
            "Connection": "keep-alive",            # Keep connection open
            "X-Accel-Buffering": "no",            # Disable nginx/proxy buffering (critical!)
            "Access-Control-Allow-Origin": "*",    # Allow CORS (or specific domain)
        }
    )
```

### 4.2 WebSocket Streaming

```python
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket streaming — better than SSE for chat UIs.
    
    Advantages over SSE:
    - Bidirectional: client can send multiple messages without reconnecting
    - Can interrupt a stream mid-generation
    - Lower overhead for high-frequency connections
    
    Message types from server:
    - {"type": "token", "text": "..."} — a generated token
    - {"type": "done", "usage": {...}} — generation complete
    - {"type": "error", "message": "..."} — error occurred
    
    Message types from client:
    - {"type": "message", "text": "...", "session_id": "..."} — user message
    - {"type": "cancel"} — cancel current generation
    """
    await websocket.accept()
    current_stream = None  # Track current stream for cancellation
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            if data.get("type") == "cancel":
                # Cancellation — close current stream if active
                # (Anthropic SDK handles cleanup automatically)
                continue
            
            if data.get("type") != "message":
                continue
            
            user_text = data.get("text", "")
            session_id = data.get("session_id", "")
            
            if not user_text.strip():
                continue
            
            # Load conversation history
            messages = await load_session_messages(session_id, user_text)
            
            # Stream response via WebSocket
            try:
                async with client_async.messages.stream(
                    model="claude-sonnet-4-6",
                    max_tokens=800,
                    system=LUMIERE_SYSTEM,
                    messages=messages,
                ) as stream:
                    
                    async for text in stream.text_stream:
                        await websocket.send_json({"type": "token", "text": text})
                    
                    final = await stream.get_final_message()
                    
                    await websocket.send_json({
                        "type": "done",
                        "usage": {
                            "input_tokens": final.usage.input_tokens,
                            "output_tokens": final.usage.output_tokens,
                        }
                    })
                    
                    # Save assistant turn to session history
                    await save_assistant_turn(session_id, final.content[0].text)
            
            except anthropic.RateLimitError:
                await websocket.send_json({"type": "error", "message": "Service busy. Please try again."})
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        await websocket.close(code=1011)
```

---

## 5. Streaming with Tool Use

Tool use pauses the stream. You must handle the pause, execute tools, and resume streaming.

### 5.1 Complete Streaming + Tool Use Loop

```python
async def stream_with_tools(
    user_message: str,
    tools: list[dict],
    tool_executors: dict[str, callable],
    system: str = "",
    max_turns: int = 10,
) -> str:
    """
    Run a streaming agentic loop with tool use.
    
    Streaming behavior:
    - Text blocks stream token by token → yield to UI immediately
    - Tool use blocks stream JSON input incrementally (not useful to show)
    - After tool execution, next text block streams again
    
    Args:
        user_message:    Initial user message
        tools:           List of tool schema dicts
        tool_executors:  Dict of {tool_name: async_callable}
        system:          System prompt
        max_turns:       Maximum tool use turns (safety limit)
    
    Yields:
        str: Text tokens as they are generated
    
    Returns:
        Complete response text
    
    Example:
        async for token in stream_with_tools("What's on tonight's menu?", TOOLS, executors):
            websocket.send_json({"type": "token", "text": token})
    """
    messages = [{"role": "user", "content": user_message}]
    full_response = ""
    
    for turn in range(max_turns):
        collected_text = ""
        tool_calls = []
        stop_reason = None
        final_message = None
        
        # ── Stream current turn ────────────────────────────────────────
        async with client_async.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            tools=tools,
            messages=messages,
        ) as stream:
            
            async for event in stream:
                event_type = getattr(event, 'type', '')
                
                if event_type == 'content_block_delta':
                    delta = getattr(event, 'delta', None)
                    if delta and getattr(delta, 'type', '') == 'text_delta':
                        # Text token — stream to UI
                        token = delta.text
                        collected_text += token
                        full_response += token
                        yield token  # ← Stream to calling code
                    
                    elif delta and getattr(delta, 'type', '') == 'input_json_delta':
                        # Tool input being streamed — not useful to show to user
                        # Could show "🔧 Looking that up..." UI indicator instead
                        pass
                
                elif event_type == 'content_block_start':
                    block = getattr(event, 'content_block', None)
                    if block and getattr(block, 'type', '') == 'tool_use':
                        # New tool call starting
                        yield f"\n[Calling tool: {block.name}...]\n"  # Optional UI feedback
            
            final_message = await stream.get_final_message()
            stop_reason = final_message.stop_reason
            
            # Add assistant's response to history
            messages.append({
                "role": "assistant",
                "content": final_message.content
            })
        
        # ── Handle stop reason ─────────────────────────────────────────
        if stop_reason == "end_turn":
            break  # Natural completion
        
        if stop_reason == "tool_use":
            # Execute all tool calls from this turn
            tool_results = []
            
            for block in final_message.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    
                    try:
                        executor = tool_executors.get(tool_name)
                        if executor:
                            # Execute tool (may be async or sync)
                            if asyncio.iscoroutinefunction(executor):
                                result = await executor(**tool_input)
                            else:
                                result = await asyncio.get_event_loop().run_in_executor(
                                    None, lambda: executor(**tool_input)
                                )
                            result_str = json.dumps(result) if not isinstance(result, str) else result
                        else:
                            result_str = json.dumps({"error": f"Unknown tool: {tool_name}"})
                    
                    except Exception as e:
                        result_str = json.dumps({"error": str(e), "tool": tool_name})
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })
            
            # Add tool results to history and continue loop
            messages.append({"role": "user", "content": tool_results})
        
        elif stop_reason == "max_tokens":
            yield "\n[Response truncated — token limit reached]\n"
            break
    
    return full_response
```

---

## 6. Streaming Event Types Reference

```python
# Complete event type reference for raw event iteration

async with client_async.messages.stream(**kwargs) as stream:
    async for event in stream:
        
        # ── Top-level message events ───────────────────────────────────
        if event.type == "message_start":
            # event.message: Message object with id, model, role, usage (initial)
            print(f"Message started: {event.message.id}")
        
        elif event.type == "message_delta":
            # event.delta.stop_reason: "end_turn" | "tool_use" | "max_tokens" | "stop_sequence"
            # event.usage: MessageDeltaUsage with output_tokens
            print(f"Stop reason: {event.delta.stop_reason}")
        
        elif event.type == "message_stop":
            # Final event — stream is ending
            pass
        
        # ── Content block events ───────────────────────────────────────
        elif event.type == "content_block_start":
            # event.index: block position (0, 1, 2...)
            # event.content_block.type: "text" | "tool_use"
            # event.content_block.id: block ID (for tool_use blocks)
            # event.content_block.name: tool name (for tool_use blocks)
            block_type = event.content_block.type
            if block_type == "tool_use":
                print(f"Tool call starting: {event.content_block.name}")
        
        elif event.type == "content_block_delta":
            # event.index: which block this delta belongs to
            # event.delta.type: "text_delta" | "input_json_delta"
            
            if event.delta.type == "text_delta":
                # event.delta.text: the text fragment
                text = event.delta.text
            
            elif event.delta.type == "input_json_delta":
                # event.delta.partial_json: partial JSON string for tool input
                partial = event.delta.partial_json
        
        elif event.type == "content_block_stop":
            # event.index: which block finished
            pass

# ── Convenience attributes on the stream object ────────────────────────
stream.current_message_snapshot   # Current assembled message state
stream.get_final_message()        # Wait for complete message (blocks until done)
stream.text_stream                 # Iterator yielding only text_delta strings
```

---

## 7. Frontend Integration Patterns

### 7.1 React — SSE Hook

```javascript
// hooks/useClaudeStream.js
import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * React hook for Claude streaming via SSE.
 * 
 * @param {string} apiUrl - SSE endpoint URL
 * @returns {Object} { text, isStreaming, isWaiting, error, ask, stop }
 * 
 * Usage:
 *   const { text, isWaiting, isStreaming, ask, stop } = useClaudeStream('/api/chat/stream');
 *   ask("What wine do you recommend?")
 */
export function useClaudeStream(apiUrl) {
    const [text, setText] = useState('');
    const [isStreaming, setIsStreaming] = useState(false);
    const [isWaiting, setIsWaiting] = useState(false);
    const [error, setError] = useState(null);
    const [usage, setUsage] = useState(null);
    const esRef = useRef(null);
    
    // Cleanup on unmount
    useEffect(() => {
        return () => { if (esRef.current) esRef.current.close(); };
    }, []);
    
    const ask = useCallback((question) => {
        // Reset state
        setText('');
        setError(null);
        setUsage(null);
        setIsWaiting(true);
        setIsStreaming(false);
        
        // Close previous connection
        if (esRef.current) {
            esRef.current.close();
            esRef.current = null;
        }
        
        // Build URL with question parameter
        const url = `${apiUrl}?question=${encodeURIComponent(question)}`;
        const es = new EventSource(url);
        esRef.current = es;
        
        es.onmessage = (event) => {
            // Handle [DONE] sentinel
            if (event.data === '[DONE]') {
                es.close();
                esRef.current = null;
                setIsStreaming(false);
                setIsWaiting(false);
                return;
            }
            
            let data;
            try {
                data = JSON.parse(event.data);
            } catch {
                return; // Invalid JSON — skip
            }
            
            // Handle errors
            if (data.error) {
                setError(data.error);
                setIsStreaming(false);
                setIsWaiting(false);
                es.close();
                return;
            }
            
            // Handle done signal with usage
            if (data.done) {
                if (data.usage) setUsage(data.usage);
                setIsStreaming(false);
                setIsWaiting(false);
                return;
            }
            
            // Handle text token
            if (data.text) {
                setIsWaiting(false);     // Hide typing indicator
                setIsStreaming(true);    // Show streaming state
                setText(prev => prev + data.text);
            }
        };
        
        es.onerror = (err) => {
            // Only report error if we were actually streaming (not a clean close)
            if (esRef.current) {
                setError('Connection lost. Please try again.');
                setIsStreaming(false);
                setIsWaiting(false);
                es.close();
                esRef.current = null;
            }
        };
    }, [apiUrl]);
    
    const stop = useCallback(() => {
        if (esRef.current) {
            esRef.current.close();
            esRef.current = null;
        }
        setIsStreaming(false);
        setIsWaiting(false);
    }, []);
    
    return { text, isStreaming, isWaiting, error, usage, ask, stop };
}
```

### 7.2 React — Chat Component

```javascript
// components/ChatWidget.jsx
import { useState } from 'react';
import { useClaudeStream } from '../hooks/useClaudeStream';

function TypingIndicator() {
    return (
        <div className="flex gap-1 p-3">
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}} />
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}} />
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}} />
        </div>
    );
}

export function ChatWidget() {
    const [input, setInput] = useState('');
    const [history, setHistory] = useState([]);
    const { text, isStreaming, isWaiting, error, usage, ask, stop } = useClaudeStream('/api/chat/stream');
    
    const handleSubmit = (e) => {
        e.preventDefault();
        if (!input.trim() || isStreaming || isWaiting) return;
        
        // Add user message to history immediately
        setHistory(h => [...h, { role: 'user', text: input }]);
        ask(input);
        setInput('');
    };
    
    // When streaming completes, add assistant turn to history
    // (detect via isStreaming transitioning false→true→false with text present)
    
    return (
        <div className="flex flex-col h-screen max-w-2xl mx-auto p-4">
            {/* History */}
            <div className="flex-1 overflow-y-auto space-y-4 mb-4">
                {history.map((msg, i) => (
                    <div key={i} className={`p-3 rounded-lg ${msg.role === 'user' ? 'bg-blue-100 ml-8' : 'bg-gray-100 mr-8'}`}>
                        {msg.text}
                    </div>
                ))}
                
                {/* Live streaming response */}
                {isWaiting && <TypingIndicator />}
                {(isStreaming || (text && !isWaiting)) && (
                    <div className="p-3 rounded-lg bg-gray-100 mr-8">
                        {text}
                        {isStreaming && <span className="animate-pulse">▋</span>}
                    </div>
                )}
                
                {error && (
                    <div className="p-3 rounded-lg bg-red-100 text-red-700">{error}</div>
                )}
            </div>
            
            {/* Input */}
            <form onSubmit={handleSubmit} className="flex gap-2">
                <input
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    placeholder="Ask about our menu, wines, or bookings..."
                    className="flex-1 p-3 border rounded-lg"
                    disabled={isStreaming || isWaiting}
                />
                {(isStreaming || isWaiting) ? (
                    <button type="button" onClick={stop} className="px-4 py-2 bg-red-500 text-white rounded-lg">
                        Stop
                    </button>
                ) : (
                    <button type="submit" className="px-4 py-2 bg-blue-500 text-white rounded-lg">
                        Send
                    </button>
                )}
            </form>
            
            {usage && (
                <div className="text-xs text-gray-400 mt-1 text-right">
                    {usage.input_tokens} → {usage.output_tokens} tokens
                </div>
            )}
        </div>
    );
}
```

### 7.3 Vanilla JavaScript (No Framework)

```javascript
// Vanilla JS SSE client — for non-React environments
function streamClaude(question, onToken, onDone, onError) {
    /**
     * Stream Claude response using raw EventSource.
     * 
     * @param {string} question - User's question
     * @param {Function} onToken - Called with each text token: (text) => void
     * @param {Function} onDone - Called when complete: ({usage}) => void
     * @param {Function} onError - Called on error: (message) => void
     * @returns {Function} Close function — call to cancel stream
     */
    const es = new EventSource(`/api/chat/stream?question=${encodeURIComponent(question)}`);
    
    es.onmessage = (e) => {
        if (e.data === '[DONE]') { es.close(); return; }
        
        const data = JSON.parse(e.data);
        if (data.error) { onError(data.error); es.close(); return; }
        if (data.done) { onDone(data.usage || {}); return; }
        if (data.text) { onToken(data.text); }
    };
    
    es.onerror = () => { onError('Connection lost'); es.close(); };
    
    return () => es.close();  // Return cancel function
}

// Usage:
let output = document.getElementById('output');
const cancelFn = streamClaude(
    "What is your tasting menu tonight?",
    (token) => { output.textContent += token; },
    (usage) => { console.log('Done:', usage); },
    (err)   => { console.error('Error:', err); }
);

// To cancel mid-stream:
// cancelFn();
```

---

## 8. Partial Response Handling

### 8.1 StreamBuffer — Accumulate and Parse

```python
import json
from dataclasses import dataclass, field

@dataclass
class StreamBuffer:
    """
    Accumulate streamed text tokens and extract complete structures as they form.
    
    Use cases:
    1. Extract a JSON object from a stream before it's complete
    2. Detect when Claude has finished a specific section
    3. Show partial markdown while streaming
    
    Usage:
        buf = StreamBuffer()
        async for text in stream.text_stream:
            buf.feed(text)
            objects = buf.try_extract_json()
            if objects:
                process_partial_json(objects[0])
    """
    _buffer: str = field(default="", init=False)
    
    def feed(self, text: str) -> None:
        """Add new text to the buffer."""
        self._buffer += text
    
    @property
    def current(self) -> str:
        """Current accumulated text."""
        return self._buffer
    
    def try_extract_json(self) -> list:
        """
        Try to extract complete JSON objects from buffer.
        Returns list of parsed objects found so far.
        Leaves incomplete JSON in buffer.
        """
        objects = []
        remaining = self._buffer
        
        while remaining:
            # Find a potential JSON start
            for start_char in ['{', '[']:
                idx = remaining.find(start_char)
                if idx == -1:
                    continue
                
                # Try to parse from this position
                candidate = remaining[idx:]
                for end in range(len(candidate), 0, -1):
                    try:
                        obj = json.loads(candidate[:end])
                        objects.append(obj)
                        remaining = candidate[end:]
                        break
                    except json.JSONDecodeError:
                        continue
                break
            else:
                break
        
        self._buffer = remaining
        return objects
    
    def extract_section(self, start_tag: str, end_tag: str) -> list[str]:
        """
        Extract completed XML-style sections from the stream.
        
        Example:
            buf.extract_section("<wine>", "</wine>") 
            → ["Château Margaux 2018, Bordeaux, £185"] (once </wine> arrives)
        """
        sections = []
        content = self._buffer
        
        while start_tag in content and end_tag in content:
            start_idx = content.index(start_tag) + len(start_tag)
            end_idx = content.index(end_tag)
            
            if start_idx < end_idx:
                sections.append(content[start_idx:end_idx])
                content = content[end_idx + len(end_tag):]
            else:
                break
        
        self._buffer = content
        return sections
    
    def lines_complete(self) -> list[str]:
        """Return all complete lines (ending with \\n) from buffer."""
        lines = self._buffer.split('\n')
        complete = lines[:-1]      # All but the last (may be incomplete)
        self._buffer = lines[-1]   # Keep the incomplete line
        return [l for l in complete if l.strip()]
```

### 8.2 Streaming JSON Extraction

```python
async def stream_and_extract_json(
    prompt: str,
    schema_description: str,
) -> dict:
    """
    Stream a JSON extraction response and parse as soon as complete.
    
    Uses prefill trick to force JSON output.
    Accumulates all text then parses at end (streaming is for UI feedback only).
    
    Returns:
        Parsed dict from Claude's JSON response
    """
    buffer = StreamBuffer()
    
    async with client_async.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[
            {"role": "user", "content": f"{prompt}\n\nSchema: {schema_description}\n\nReturn valid JSON only."},
            {"role": "assistant", "content": "{"},  # Prefill forces JSON start
        ]
    ) as stream:
        async for text in stream.text_stream:
            buffer.feed(text)
            # Optionally: print progress indicator to console
    
    # Complete JSON is "{" (prefill) + buffered content
    raw = "{" + buffer.current
    
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try fixing truncated JSON
        return parse_claude_json(raw)  # See structured-output.md
```

---

## 9. Error Handling in Streams

### 9.1 Stream-Specific Error Patterns

```python
import anthropic
from anthropic import (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    APIStatusError,
    BadRequestError,
)

async def robust_stream(
    messages: list,
    system: str = "",
    max_retries: int = 3,
    timeout_seconds: float = 120.0,
) -> str:
    """
    Stream with comprehensive error handling and retry logic.
    
    Retry behavior:
    - RateLimitError (429): Retry with backoff, respect Retry-After header
    - APIStatusError 500/529: Retry with backoff
    - APIConnectionError: Retry immediately (likely transient)
    - BadRequestError (400): Do NOT retry — fix the request
    - TimeoutError: Fall back to non-streaming call with longer timeout
    
    Returns:
        Complete response text (may be from stream or fallback)
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            return await _attempt_stream(messages, system, timeout_seconds)
        
        except RateLimitError as e:
            last_error = e
            if attempt < max_retries - 1:
                retry_after = float(getattr(e.response, 'headers', {}).get('retry-after', 5))
                wait = min(retry_after * (2 ** attempt) + random.uniform(0, 1), 60)
                await asyncio.sleep(wait)
        
        except APIStatusError as e:
            last_error = e
            if e.status_code in {500, 529} and attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt + random.uniform(0, 1))
            else:
                raise  # Don't retry 400s etc.
        
        except (APIConnectionError, APITimeoutError) as e:
            last_error = e
            if attempt < max_retries - 1:
                await asyncio.sleep(1)  # Brief wait for transient issues
        
        except BadRequestError:
            raise  # Never retry bad requests — fix the prompt
    
    raise last_error  # All retries exhausted

async def _attempt_stream(messages: list, system: str, timeout: float) -> str:
    """Single streaming attempt with timeout."""
    full_text = ""
    
    async with asyncio.timeout(timeout):
        async with client_async.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                full_text += text
    
    return full_text
```

### 9.2 Graceful Streaming Degradation

```python
async def stream_with_fallback(
    question: str,
    websocket = None,
):
    """
    Try streaming; fall back to non-streaming if stream fails mid-way.
    
    If the stream fails after some tokens have been sent, we continue
    with a non-streaming call to complete the response.
    """
    partial_text = ""
    
    try:
        async with client_async.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": question}],
        ) as stream:
            async for text in stream.text_stream:
                partial_text += text
                if websocket:
                    await websocket.send_json({"type": "token", "text": text})
        
        return partial_text
    
    except (APIConnectionError, APITimeoutError) as e:
        if partial_text:
            # We got some text — try to complete the thought
            try:
                completion = await client_async.messages.create(
                    model="claude-haiku-4-5-20251001",  # Fallback to faster model
                    max_tokens=200,
                    messages=[
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": partial_text + "... [continuing]"},
                        {"role": "user", "content": "Please complete your previous response briefly."}
                    ]
                )
                suffix = completion.content[0].text
                if websocket:
                    await websocket.send_json({"type": "token", "text": suffix})
                return partial_text + suffix
            except Exception:
                pass  # Accept partial response
        
        if websocket:
            await websocket.send_json({"type": "error", "message": "Stream interrupted. Partial response shown."})
        return partial_text
```

---

## 10. Advanced: Structured Output via Streaming

Stream structured data and process it progressively.

```python
async def stream_structured_items(
    document: str,
    item_type: str = "wine",
) -> asyncio.AsyncGenerator[dict, None]:
    """
    Stream a list of structured items progressively.
    Claude produces them one at a time; we yield each as soon as it's complete.
    
    This is great for large lists where you want to start displaying
    items before the full list is generated.
    
    Usage:
        async for wine in stream_structured_items(wine_list_text, "wine"):
            await render_wine_card(wine)
    """
    buffer = StreamBuffer()
    
    system = f"""Extract {item_type} items from the text. Output one JSON object per line.
Each object on its own line, no commas between objects (JSONL format):
{{"name": "...", "vintage": ..., "price": ..., "description": "..."}}
{{"name": "...", "vintage": ..., "price": ..., "description": "..."}}"""
    
    async with client_async.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=system,
        messages=[{"role": "user", "content": document}],
    ) as stream:
        async for text in stream.text_stream:
            buffer.feed(text)
            
            # Extract complete JSONL lines as they arrive
            for line in buffer.lines_complete():
                if line.startswith('{'):
                    try:
                        item = json.loads(line)
                        yield item  # Yield each item as soon as it's ready
                    except json.JSONDecodeError:
                        pass  # Skip malformed lines
```

---

## 11. Performance Considerations

### Streaming Overhead

```python
# Streaming adds ~50-100ms overhead compared to non-streaming
# due to chunked transfer encoding setup.

# Non-streaming: faster for scripts, batch processing
# Streaming:     essential for user-facing interfaces

# Rule: stream when a human is watching; don't stream for machine-to-machine

STREAMING_OVERHEAD_MS = 75  # Approximate

# For a 500-token response at 100 tokens/sec = 5,000ms generation time
# Non-streaming: user waits 5,075ms then sees everything
# Streaming:     user sees first word at ~675ms, done at 5,075ms
# UX improvement: 88% reduction in perceived latency
```

### Buffer Flushing

```python
# CRITICAL: Always flush buffers immediately in streaming code

# ❌ Will buffer multiple tokens before printing
print(text, end="")  # Buffered output

# ✅ Writes each token immediately
print(text, end="", flush=True)

# In asyncio generators:
# yield handles flushing automatically — no extra work needed
```

---

## 12. Junior Walkthrough — Add Streaming to Existing App

**Scenario**: You have a working Claude chat app but users complain about the 3-5 second wait time.

**Step 1**: Change your existing non-streaming call to streaming

```python
# BEFORE (non-streaming):
def get_response(question: str) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text

# AFTER (streaming — barely any code change):
def get_response_streaming(question: str) -> str:
    full_text = ""
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": question}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)   # Show to user as it arrives
            full_text += text
    return full_text
```

**Step 2**: Wrap it in a FastAPI SSE endpoint (5 minutes of work)

```python
# Add to your existing FastAPI app
@app.get("/api/stream")
async def stream(question: str):
    async def generate():
        async with client_async.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": question}],
        ) as stream:
            async for text in stream.text_stream:
                yield f"data: {json.dumps({'text': text})}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream",
                              headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
```

**Step 3**: Connect from your frontend

```javascript
const es = new EventSource(`/api/stream?question=${encodeURIComponent(question)}`);
let output = "";
es.onmessage = (e) => {
    if (e.data === "[DONE]") { es.close(); return; }
    output += JSON.parse(e.data).text;
    document.getElementById("response").textContent = output;
};
```

**That's it** — you now have streaming from server to browser.

---

## 13. Senior Patterns — Production Streaming Infrastructure

### Backpressure Handling

```python
import asyncio

async def stream_with_backpressure(
    question: str,
    websocket: WebSocket,
    max_queue_size: int = 100,
):
    """
    Stream to WebSocket with backpressure — if client is slow,
    buffer tokens in a queue and process them as fast as client can handle.
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
    
    async def producer():
        """Generate tokens and put in queue."""
        async with client_async.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": question}],
        ) as stream:
            async for text in stream.text_stream:
                await queue.put(("token", text))
        await queue.put(("done", None))
    
    async def consumer():
        """Consume from queue and send to WebSocket."""
        while True:
            event_type, data = await queue.get()
            if event_type == "done":
                await websocket.send_json({"type": "done"})
                break
            await websocket.send_json({"type": "token", "text": data})
            queue.task_done()
    
    # Run producer and consumer concurrently
    await asyncio.gather(producer(), consumer())
```

---

## 14. Tips, Tricks, and Gotchas

### Tips

1. **Always capture `get_final_message()`** — this is where you get token usage for cost tracking
2. **`X-Accel-Buffering: no` header** — without this, nginx will buffer your SSE stream and the client sees nothing until buffering flushes
3. **Reconnect logic on client** — SSE auto-reconnects after 3 seconds by default; set `retry:` field in event to control this
4. **Token-by-token vs word-by-word display** — for better visual smoothness, batch short tokens into words before rendering

### Tricks

5. **`text_stream` vs raw event iteration** — `text_stream` is simpler; iterate raw events when you need to intercept tool_use blocks
6. **Prefill works with streaming** — add `{"role": "assistant", "content": "{"}` to force JSON output even while streaming
7. **Content-Type matters** — `text/event-stream` for SSE; `application/octet-stream` for raw binary streams
8. **EventSource URL limit** — browsers cap URL length at ~2,000 characters; use POST + WebSocket for long messages

### Gotchas

9. **SSE is one-way** — client can't send data back on the same connection; use WebSocket for bidirectional
10. **`flush=True` is not optional** — Python's print buffers by default; without `flush=True`, nothing appears until buffer fills
11. **Don't await `get_final_message()` before consuming the stream** — you must exhaust `text_stream` first or you'll deadlock
12. **Async generator cleanup** — if a client disconnects mid-stream, your `generate()` coroutine gets garbage collected; no explicit cleanup needed but don't hold locks
13. **Tool use stops text streaming** — during `input_json_delta` events, no text is flowing; show a "thinking" indicator in the UI

---

## 15. Quick Reference Cheatsheet

```python
# ═══════════════════════════════════════════════════════════════
# STREAMING QUICK REFERENCE
# ═══════════════════════════════════════════════════════════════

# 1. SYNCHRONOUS STREAMING (simplest)
with client.messages.stream(model=..., max_tokens=..., messages=[...]) as s:
    for text in s.text_stream:
        print(text, end="", flush=True)   # flush=True required
    final = s.get_final_message()         # Always capture this

# 2. ASYNC STREAMING
async with client_async.messages.stream(...) as s:
    async for text in s.text_stream:
        yield f"data: {json.dumps({'text': text})}\n\n"   # SSE format
    yield "data: [DONE]\n\n"

# 3. SSE RESPONSE HEADERS (required)
headers = {
    "Cache-Control": "no-cache",    # Don't cache the stream
    "X-Accel-Buffering": "no",     # Disable nginx buffering
}
return StreamingResponse(generate(), media_type="text/event-stream", headers=headers)

# 4. FRONTEND SSE
const es = new EventSource('/api/stream?q=' + encodeURIComponent(q));
es.onmessage = (e) => {
    if (e.data === '[DONE]') { es.close(); return; }
    const { text } = JSON.parse(e.data);
    document.getElementById('out').textContent += text;
};

# 5. STREAMING WITH TOOLS (key loop)
async with client_async.messages.stream(..., tools=TOOLS) as stream:
    async for event in stream:
        if event.type == 'content_block_delta' and event.delta.type == 'text_delta':
            yield event.delta.text
    final = await stream.get_final_message()
    if final.stop_reason == 'tool_use':
        results = await execute_tools(final.content)
        messages.append(...)   # Continue loop

# 6. STOP REASONS
# end_turn     → Natural completion
# tool_use     → Execute tools and continue
# max_tokens   → Hit token limit — increase max_tokens or trim prompt
# stop_sequence → Hit custom stop sequence

# 7. EVENT TYPES
# message_start        → Stream beginning
# content_block_start  → New text or tool_use block starting
# content_block_delta  → text_delta OR input_json_delta
# content_block_stop   → Block finished
# message_delta        → stop_reason available
# message_stop         → Stream ending
```
