# batch-processing.md — Claude Message Batches API

> **Purpose**: How to use the Anthropic Message Batches API for high-volume async processing at 50% cost reduction. Covers batch creation, polling, result collection, error handling, cancellation, pipeline patterns, and Azure integration.  
> **Owner**: jose@hybridgenai.com | **Updated**: 2026-05-22  
> **Applies to**: claude-haiku-4-5-20251001, claude-sonnet-4-6, claude-opus-4-6

---

## Navigation

1. [When to Use Batch vs Synchronous](#1-when-to-use-batch-vs-synchronous)
2. [Batch API Fundamentals](#2-batch-api-fundamentals)
3. [Creating a Batch](#3-creating-a-batch)
4. [Polling Strategies](#4-polling-strategies)
5. [Retrieving and Parsing Results](#5-retrieving-and-parsing-results)
6. [Error Handling in Batches](#6-error-handling-in-batches)
7. [Cancellation and Lifecycle Management](#7-cancellation-and-lifecycle-management)
8. [Full Production Pipeline](#8-full-production-pipeline)
9. [Cost Comparison and ROI](#9-cost-comparison-and-roi)
10. [Batch API with Prompt Caching](#10-batch-api-with-prompt-caching)
11. [Azure-Integrated Batch Pipeline](#11-azure-integrated-batch-pipeline)
12. [Monitoring and Alerting](#12-monitoring-and-alerting)
13. [Junior Developer Walkthrough](#13-junior-developer-walkthrough)
14. [Senior Developer Patterns](#14-senior-developer-patterns)
15. [Tips, Tricks, and Gotchas](#15-tips-tricks-and-gotchas)
16. [Quick Reference Cheatsheet](#16-quick-reference-cheatsheet)

---

## Who This Is For

**Juniors**: Read sections 1, 2, 3, 5, 13 — understand the mental model before writing code.  
**Seniors**: Jump to sections 8, 10, 11, 14 — production patterns, caching integration, Azure pipelines.  
**Everyone**: Section 15 (gotchas) and 16 (cheatsheet) before deploying anything.

---

## 1. When to Use Batch vs Synchronous

The core rule: **if a human is waiting, use sync; if a pipeline can wait hours, use batch**.

### Decision Table

| Scenario | Batch API | Sync API | Why |
|----------|-----------|----------|-----|
| Nightly invoice processing | ✅ Perfect | ❌ Expensive | Runs at 2am, no user waiting |
| Real-time guest chat | ❌ Too slow | ✅ Required | User expects <3s response |
| Bulk menu description rewriting | ✅ | ❌ | Hundreds of items, no urgency |
| Allergen info lookup | ❌ | ✅ | Safety-critical, immediate |
| Daily wine label analysis (new arrivals) | ✅ | ❌ | Runs before service |
| Evaluation dataset scoring | ✅ | ❌ | 500+ items, overnight job |
| Document classification (weekly) | ✅ | ❌ | Not time-sensitive |
| Customer complaint triage (live) | ❌ | ✅ | Must respond immediately |
| Generating monthly guest report | ✅ | ❌ | Runs at month-end |
| Reservation confirmation drafts | ❌ | ✅ | User waiting for confirmation |

### The 4 Questions

Ask these before choosing:

1. **Is a human actively waiting?** → Sync
2. **Does it need to complete in <30 seconds?** → Sync
3. **Do I need the result before the next user action?** → Sync
4. **Is this a scheduled background job?** → Batch

### Cost/Latency Trade-off

```
Sync API:   Full price     | Result in seconds     | Rate limited
Batch API:  50% discount   | Result in min-hours   | Higher throughput
```

---

## 2. Batch API Fundamentals

### What the Batch API Does

The Batch API accepts up to **10,000 requests** in a single batch submission. Anthropic processes them asynchronously and you poll for results. This avoids:
- Per-request rate limit bottlenecks
- Managing thousands of concurrent async calls
- Paying full price for non-urgent workloads

### Key Concepts

```
Batch ID:       Unique identifier returned on creation (e.g., "msgbatch_01...")
custom_id:      YOUR identifier for each request (e.g., "invoice-0042")
processing_status:
    - "in_progress"  → Still processing
    - "ended"        → All requests completed (success + error)
    - "canceling"    → Cancel requested, winding down
    - "canceled"     → Successfully canceled

Request counts (in batch.request_counts):
    - succeeded     → Completed without error
    - errored       → Failed with error
    - processing    → Still in queue or running
    - canceled      → Canceled before processing
    - expired       → Batch expired before processing (24-hour TTL)
```

### Lifecycle Diagram

```
submit_batch()
      ↓
  in_progress
      ↓  (poll every 60-300s)
    ended
      ↓
collect_results()
      ↓
  Process succeeded
  Handle errored
  Re-submit failed
```

### Limits and Constraints (2026)

| Parameter | Limit |
|-----------|-------|
| Max requests per batch | 10,000 |
| Max total tokens per batch | 100M |
| Batch expiry (if not completed) | 24 hours |
| Result retrieval window | 29 days |
| Minimum poll interval | 10 seconds (respect rate limits) |
| Supported models | All Claude models |

---

## 3. Creating a Batch

### Basic Batch Creation

```python
import anthropic
import json
from pathlib import Path

client = anthropic.Anthropic()
# Default: reads ANTHROPIC_API_KEY from environment

def process_invoices_batch(invoice_texts: list[str]) -> str:
    """
    Submit invoices for overnight batch processing.
    
    Args:
        invoice_texts: Raw text of each invoice
        
    Returns:
        batch_id: Use this to poll and retrieve results
        
    Default model: claude-haiku-4-5-20251001 (cheapest extraction model)
    Default max_tokens: 300 (invoices rarely need more)
    """
    requests = []
    for i, invoice_text in enumerate(invoice_texts):
        requests.append(
            anthropic.types.message_create_params.Request(
                custom_id=f"invoice-{i:04d}",  # Zero-padded for easy sorting
                params=anthropic.types.MessageCreateParamsNonStreaming(
                    model="claude-haiku-4-5-20251001",  # Cheapest for structured extraction
                    max_tokens=300,                      # Tight budget — invoices are short JSON
                    messages=[{
                        "role": "user",
                        "content": f"""Extract these fields from the invoice below.
Return a JSON object with exactly these keys:
- vendor_name (string)
- invoice_date (string, YYYY-MM-DD format)
- total_amount (number, no currency symbol)
- currency (string, 3-letter ISO code like USD, GBP, EUR)
- line_items (array of objects with: description, quantity, unit_price, total)

If a field is missing, use null. Return ONLY the JSON, no explanation.

Invoice:
{invoice_text}"""
                    }],
                )
            )
        )
    
    batch = client.beta.messages.batches.create(requests=requests)
    
    print(f"✅ Batch created: {batch.id}")
    print(f"📊 {len(requests)} requests submitted")
    print(f"⏱️  Estimated completion: few minutes to a few hours")
    print(f"🕐 Expires at: {batch.expires_at}")
    
    # Save batch_id for recovery — critical if your process restarts
    save_batch_id_to_storage(batch.id, metadata={"job": "invoice_extraction", "count": len(requests)})
    
    return batch.id


def save_batch_id_to_storage(batch_id: str, metadata: dict):
    """Persist batch_id so pipeline can resume after restart."""
    record = {"batch_id": batch_id, "created_at": str(datetime.utcnow()), **metadata}
    with open("pending_batches.jsonl", "a") as f:
        f.write(json.dumps(record) + "\n")
```

### Batch with Different Models per Request

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class BatchRequest:
    custom_id: str
    user_message: str
    model: str = "claude-haiku-4-5-20251001"   # Default: cheapest
    max_tokens: int = 500
    system_prompt: Optional[str] = None
    temperature: float = 0.0                    # 0.0 for consistent extraction

def create_mixed_model_batch(requests: list[BatchRequest]) -> str:
    """
    Submit batch where different requests use different models.
    
    Use case: Simple classification → Haiku, complex analysis → Sonnet
    """
    batch_requests = []
    
    for req in requests:
        messages = [{"role": "user", "content": req.user_message}]
        
        params = {
            "model": req.model,
            "max_tokens": req.max_tokens,
            "messages": messages,
            "temperature": req.temperature,
        }
        
        if req.system_prompt:
            params["system"] = req.system_prompt
        
        batch_requests.append(
            anthropic.types.message_create_params.Request(
                custom_id=req.custom_id,
                params=anthropic.types.MessageCreateParamsNonStreaming(**params),
            )
        )
    
    batch = client.beta.messages.batches.create(requests=batch_requests)
    return batch.id


# Example: Lumière restaurant nightly batch with mixed models
def build_restaurant_nightly_batch(menu_items, invoices, reviews):
    """Build a mixed batch for Lumière's nightly processing."""
    requests = []
    
    # Low complexity: classify reviews with Haiku
    for i, review in enumerate(reviews):
        requests.append(BatchRequest(
            custom_id=f"review-classify-{i:04d}",
            user_message=f"Classify this review sentiment: {review}\n\nReturn: positive/negative/neutral",
            model="claude-haiku-4-5-20251001",
            max_tokens=5,     # Just the classification word
        ))
    
    # Medium complexity: rewrite menu descriptions with Sonnet
    for i, item in enumerate(menu_items):
        requests.append(BatchRequest(
            custom_id=f"menu-rewrite-{i:04d}",
            user_message=f"Rewrite this menu description with elegant, evocative language (50 words max):\n\n{item['description']}",
            model="claude-sonnet-4-6",
            max_tokens=150,
            system_prompt="You are a world-class restaurant copywriter specializing in fine dining.",
        ))
    
    # Low complexity: extract invoice fields with Haiku
    for i, invoice in enumerate(invoices):
        requests.append(BatchRequest(
            custom_id=f"invoice-{i:04d}",
            user_message=f"Extract: vendor_name, date, total, currency. Return JSON only.\n\n{invoice}",
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
        ))
    
    return create_mixed_model_batch(requests)
```

### Batch with System Prompts

```python
LUMIERE_BATCH_SYSTEM = """You are a data extraction assistant for Lumière, a fine dining restaurant.
Always return valid JSON. Never include explanations outside the JSON object.
If data is ambiguous, use your best judgment and set a "confidence" field (0.0-1.0).
Currency should be ISO 4217 format (USD, GBP, EUR, JPY)."""

def create_batch_with_system_prompt(texts: list[str], task_prompt_template: str) -> str:
    """Create batch where all requests share the same system prompt."""
    requests = [
        anthropic.types.message_create_params.Request(
            custom_id=f"item-{i:05d}",
            params=anthropic.types.MessageCreateParamsNonStreaming(
                model="claude-haiku-4-5-20251001",
                max_tokens=400,
                system=LUMIERE_BATCH_SYSTEM,
                messages=[{"role": "user", "content": task_prompt_template.format(text=text)}],
            )
        )
        for i, text in enumerate(texts)
    ]
    batch = client.beta.messages.batches.create(requests=requests)
    return batch.id
```

---

## 4. Polling Strategies

### Basic Polling (Simple Jobs)

```python
import time
from datetime import datetime

def wait_for_batch(batch_id: str, poll_interval_seconds: int = 60) -> str:
    """
    Poll until batch completes. Returns final status.
    
    Default poll_interval_seconds=60: reasonable for most jobs
    For overnight jobs: use 300 (5 minutes) to save API calls
    For time-sensitive jobs: use 30 (minimum reasonable)
    Never poll faster than 10s — you'll hit rate limits
    """
    start_time = datetime.utcnow()
    
    while True:
        batch = client.beta.messages.batches.retrieve(batch_id)
        counts = batch.request_counts
        elapsed = (datetime.utcnow() - start_time).seconds
        
        print(f"[{elapsed:>6}s] Status: {batch.processing_status:12s} | "
              f"✅ {counts.succeeded:>5} | ❌ {counts.errored:>4} | "
              f"⏳ {counts.processing:>5} | ⏸️ {counts.canceled:>4}")
        
        if batch.processing_status == "ended":
            print(f"\n🏁 Batch {batch_id} completed in {elapsed}s")
            return batch.processing_status
        
        if batch.processing_status in ("canceled", "canceling"):
            print(f"\n⚠️ Batch {batch_id} was canceled")
            return batch.processing_status
        
        time.sleep(poll_interval_seconds)


# Example output:
# [    0s] Status: in_progress  | ✅    45 | ❌    2 | ⏳   453 | ⏸️    0
# [   60s] Status: in_progress  | ✅   312 | ❌    8 | ⏳   180 | ⏸️    0
# [  120s] Status: ended        | ✅   488 | ❌   12 | ⏳     0 | ⏸️    0
```

### Exponential Backoff Polling (Production)

```python
import asyncio
from typing import Optional

async def poll_batch_async(
    batch_id: str,
    initial_interval: float = 30.0,    # Start checking every 30s
    max_interval: float = 300.0,       # Cap at 5 minutes
    backoff_factor: float = 1.5,       # Multiply interval by this each check
    timeout_hours: float = 24.0,       # Give up after 24 hours
    progress_callback=None,            # Optional: function(counts) called each poll
) -> str:
    """
    Adaptive polling: starts frequent, slows down for long jobs.
    
    For a 1000-item batch:
    - Checks at: 30s, 45s, 67s, 101s, 152s, 228s, 300s, 300s, 300s...
    - Saves ~40% polling overhead vs fixed interval
    """
    interval = initial_interval
    start_time = asyncio.get_event_loop().time()
    timeout_seconds = timeout_hours * 3600
    
    while True:
        elapsed = asyncio.get_event_loop().time() - start_time
        
        if elapsed > timeout_seconds:
            raise TimeoutError(f"Batch {batch_id} did not complete within {timeout_hours}h")
        
        batch = client.beta.messages.batches.retrieve(batch_id)
        
        if progress_callback:
            progress_callback(batch.request_counts)
        
        if batch.processing_status == "ended":
            return batch.processing_status
        
        if batch.processing_status in ("canceled", "canceling"):
            return batch.processing_status
        
        await asyncio.sleep(interval)
        interval = min(interval * backoff_factor, max_interval)


# Progress callback example
def on_progress(counts):
    total = counts.succeeded + counts.errored + counts.processing + counts.canceled
    pct = (counts.succeeded + counts.errored) / total * 100 if total > 0 else 0
    print(f"Progress: {pct:.1f}% | ✅{counts.succeeded} ❌{counts.errored} ⏳{counts.processing}")
```

### Webhook-Style Polling with Database State

```python
import sqlite3
from enum import Enum

class BatchJobStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    COMPLETED = "completed"
    FAILED = "failed"

class BatchJobTracker:
    """Track batch job state in SQLite for durability across restarts."""
    
    def __init__(self, db_path: str = "batch_jobs.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_db()
    
    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS batch_jobs (
                job_name TEXT PRIMARY KEY,
                batch_id TEXT,
                status TEXT DEFAULT 'pending',
                submitted_at TEXT,
                completed_at TEXT,
                succeeded_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                metadata TEXT  -- JSON blob
            )
        """)
        self.conn.commit()
    
    def register_job(self, job_name: str, batch_id: str, metadata: dict = None):
        self.conn.execute("""
            INSERT OR REPLACE INTO batch_jobs 
            (job_name, batch_id, status, submitted_at, metadata)
            VALUES (?, ?, 'submitted', datetime('now'), ?)
        """, (job_name, batch_id, json.dumps(metadata or {})))
        self.conn.commit()
    
    def mark_completed(self, job_name: str, succeeded: int, failed: int):
        self.conn.execute("""
            UPDATE batch_jobs SET
                status='completed', completed_at=datetime('now'),
                succeeded_count=?, failed_count=?
            WHERE job_name=?
        """, (succeeded, failed, job_name))
        self.conn.commit()
    
    def get_pending_jobs(self) -> list[dict]:
        """Resume tracking after process restart."""
        cursor = self.conn.execute(
            "SELECT job_name, batch_id FROM batch_jobs WHERE status='submitted'"
        )
        return [{"job_name": row[0], "batch_id": row[1]} for row in cursor.fetchall()]
```

---

## 5. Retrieving and Parsing Results

### Basic Result Collection

```python
def collect_batch_results(batch_id: str) -> dict[str, dict]:
    """
    Retrieve all results from a completed batch.
    
    Returns dict keyed by custom_id, values are:
        {"status": "success", "data": {...}, "tokens": 342}  # for succeeded
        {"status": "parse_error", "raw": "...", "tokens": 201}  # JSON parse failure
        {"status": "error", "error_type": "...", "message": "..."}  # API error
    """
    results = {}
    
    for result in client.beta.messages.batches.results(batch_id):
        custom_id = result.custom_id
        
        if result.result.type == "succeeded":
            message = result.result.message
            raw_text = message.content[0].text
            
            try:
                # Try to parse as JSON first
                parsed_data = json.loads(raw_text)
                results[custom_id] = {
                    "status": "success",
                    "data": parsed_data,
                    "tokens": message.usage.input_tokens + message.usage.output_tokens,
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                }
            except json.JSONDecodeError:
                # Text response (non-JSON tasks)
                results[custom_id] = {
                    "status": "success",
                    "data": raw_text,
                    "is_json": False,
                    "tokens": message.usage.input_tokens + message.usage.output_tokens,
                }
        
        elif result.result.type == "errored":
            error = result.result.error
            results[custom_id] = {
                "status": "error",
                "error_type": error.type,
                "message": str(error),
            }
            # Common error types:
            # "invalid_request"  → Bad parameters (not retryable)
            # "overloaded"       → Server busy (retry with smaller batch)
            # "rate_limit"       → Should not happen in batch; log if seen
    
    return results
```

### Streaming Results (Memory-Efficient for Large Batches)

```python
def stream_batch_results_to_disk(batch_id: str, output_file: str):
    """
    Write results directly to disk instead of loading all into memory.
    
    Use this for batches > 1,000 items to avoid memory issues.
    Each line is a JSONL record.
    """
    succeeded = 0
    failed = 0
    
    with open(output_file, "w") as f:
        for result in client.beta.messages.batches.results(batch_id):
            record = {
                "custom_id": result.custom_id,
                "type": result.result.type,
            }
            
            if result.result.type == "succeeded":
                msg = result.result.message
                record.update({
                    "text": msg.content[0].text,
                    "input_tokens": msg.usage.input_tokens,
                    "output_tokens": msg.usage.output_tokens,
                    "stop_reason": msg.stop_reason,
                })
                succeeded += 1
            else:
                record.update({
                    "error_type": result.result.error.type,
                    "error_message": str(result.result.error),
                })
                failed += 1
            
            f.write(json.dumps(record) + "\n")
    
    print(f"Results saved: {succeeded} succeeded, {failed} failed → {output_file}")
    return {"succeeded": succeeded, "failed": failed, "output_file": output_file}


def load_and_parse_results_jsonl(results_file: str) -> dict[str, dict]:
    """
    Load previously saved JSONL results and parse JSON content.
    Works with results saved by stream_batch_results_to_disk().
    """
    results = {}
    with open(results_file) as f:
        for line in f:
            record = json.loads(line.strip())
            custom_id = record.pop("custom_id")
            
            # Try to parse text as JSON
            if record.get("type") == "succeeded" and "text" in record:
                try:
                    record["parsed"] = json.loads(record["text"])
                    record["parse_success"] = True
                except json.JSONDecodeError:
                    record["parse_success"] = False
            
            results[custom_id] = record
    
    return results
```

### Robust JSON Extraction (Handle Markdown Code Blocks)

```python
import re

def extract_json_from_response(text: str) -> dict:
    """
    Extract JSON from Claude's response even if wrapped in markdown.
    
    Claude sometimes outputs:
        ```json
        {"key": "value"}
        ```
    Instead of just: {"key": "value"}
    
    This handles both cases.
    """
    # Strip markdown code blocks if present
    patterns = [
        r"```json\s*([\s\S]*?)\s*```",   # ```json ... ```
        r"```\s*([\s\S]*?)\s*```",         # ``` ... ```
        r"\{[\s\S]*\}",                     # Raw JSON object
        r"\[[\s\S]*\]",                     # Raw JSON array
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            candidate = match.group(1) if "json" in pattern or pattern.startswith("```") else match.group(0)
            try:
                return json.loads(candidate.strip())
            except json.JSONDecodeError:
                continue
    
    raise ValueError(f"Could not extract JSON from response: {text[:200]}")


def safe_parse_batch_result(text: str, custom_id: str) -> dict:
    """
    Parse batch result with fallback and error tagging.
    Returns the parsed data or error info — never raises.
    """
    try:
        return {"status": "ok", "data": extract_json_from_response(text)}
    except ValueError:
        # Log for reprocessing
        return {
            "status": "parse_error",
            "raw": text[:500],
            "custom_id": custom_id,
        }
```

---

## 6. Error Handling in Batches

### Categorizing and Re-submitting Failed Requests

```python
from dataclasses import dataclass, field

@dataclass
class BatchFailureAnalysis:
    retryable: list[str] = field(default_factory=list)   # custom_ids to retry
    permanent: list[str] = field(default_factory=list)   # custom_ids to skip
    parse_errors: list[str] = field(default_factory=list) # custom_ids to retry with different prompt


def analyse_batch_failures(results: dict[str, dict]) -> BatchFailureAnalysis:
    """
    Categorize failures to decide what to retry vs abandon.
    
    Retryable: overloaded, server errors
    Permanent: invalid_request (bad params won't help to retry)
    Parse errors: succeeded but JSON was malformed (retry with stricter prompt)
    """
    analysis = BatchFailureAnalysis()
    
    RETRYABLE_ERROR_TYPES = {"overloaded", "api_error", "server_error"}
    PERMANENT_ERROR_TYPES = {"invalid_request", "authentication_error", "permission_error"}
    
    for custom_id, result in results.items():
        if result["status"] == "error":
            error_type = result.get("error_type", "unknown")
            if error_type in RETRYABLE_ERROR_TYPES:
                analysis.retryable.append(custom_id)
            else:
                analysis.permanent.append(custom_id)
        elif result["status"] == "parse_error":
            analysis.parse_errors.append(custom_id)
    
    return analysis


def resubmit_failed_requests(
    original_requests: dict[str, dict],  # Map of custom_id → original request params
    custom_ids_to_retry: list[str],
    stricter_prompt: bool = False,
) -> str:
    """
    Create a new batch with only the failed requests.
    Optionally uses a stricter JSON prompt for parse errors.
    """
    retry_requests = []
    
    for custom_id in custom_ids_to_retry:
        params = original_requests[custom_id].copy()
        
        if stricter_prompt:
            # Add explicit JSON enforcement to prompt
            original_msg = params["messages"][0]["content"]
            params["messages"][0]["content"] = (
                original_msg + 
                "\n\nIMPORTANT: Return ONLY a valid JSON object. No markdown, no explanation. "
                "Start your response with { and end with }."
            )
        
        retry_requests.append(
            anthropic.types.message_create_params.Request(
                custom_id=custom_id,
                params=anthropic.types.MessageCreateParamsNonStreaming(**params),
            )
        )
    
    batch = client.beta.messages.batches.create(requests=retry_requests)
    print(f"♻️  Retry batch created: {batch.id} ({len(retry_requests)} items)")
    return batch.id
```

### Merge Results from Multiple Batches

```python
def merge_batch_results(*result_dicts: dict[str, dict]) -> dict[str, dict]:
    """
    Merge results from original batch + retry batches.
    Later batches overwrite earlier ones (retry wins).
    
    Usage:
        original_results = collect_batch_results(batch_id_1)
        retry_results = collect_batch_results(batch_id_2)
        final = merge_batch_results(original_results, retry_results)
    """
    merged = {}
    for results in result_dicts:
        merged.update(results)  # Later dicts overwrite earlier ones
    return merged
```

---

## 7. Cancellation and Lifecycle Management

### Canceling a Batch

```python
def cancel_batch(batch_id: str) -> bool:
    """
    Cancel a batch that's in progress.
    
    When to cancel:
    - Input data was incorrect and you need to resubmit
    - Business requirements changed (e.g., menu update superseded)
    - Batch is taking too long and you need results now (switch to sync)
    
    Note: Results for requests already processed BEFORE cancel are still available.
    """
    try:
        batch = client.beta.messages.batches.cancel(batch_id)
        print(f"Cancel requested for {batch_id}. Status: {batch.processing_status}")
        # Status will be "canceling" → eventually "canceled"
        return True
    except anthropic.APIError as e:
        print(f"Cancel failed: {e}")
        return False


def list_active_batches() -> list[dict]:
    """
    List all active (in_progress) batches to monitor or cancel stale ones.
    Useful for cleanup after process restarts.
    """
    active = []
    for batch in client.beta.messages.batches.list():
        if batch.processing_status == "in_progress":
            active.append({
                "id": batch.id,
                "status": batch.processing_status,
                "succeeded": batch.request_counts.succeeded,
                "processing": batch.request_counts.processing,
                "expires_at": str(batch.expires_at),
            })
    return active
```

---

## 8. Full Production Pipeline

### Complete Nightly Invoice Pipeline

```python
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger("lumiere.batch")


async def nightly_invoice_pipeline(
    max_retries: int = 2,
    poll_interval: int = 300,       # Poll every 5 minutes overnight
    max_wait_hours: float = 22.0,   # Must complete before morning service
) -> dict:
    """
    Complete nightly batch processing for Lumière restaurant invoices.
    
    Runs at 02:00, must complete before 08:00 (6-hour window).
    Processes all new invoices from Azure Blob Storage.
    Saves extracted data to Azure SQL Database.
    
    Returns: {"succeeded": N, "failed": N, "cost_usd": float}
    """
    pipeline_start = datetime.utcnow()
    total_succeeded = 0
    total_failed = 0
    
    # ── Step 1: Load invoices from Azure Blob Storage ──────────────────────
    logger.info("Loading new invoices from Azure Blob Storage...")
    invoices = await load_new_invoices_from_blob(container="invoices-incoming")
    logger.info(f"Found {len(invoices)} new invoices")
    
    if not invoices:
        logger.info("No invoices to process. Pipeline complete.")
        return {"succeeded": 0, "failed": 0, "cost_usd": 0.0}
    
    # ── Step 2: Split into chunks of 1000 (batch limit is 10000, be conservative) ──
    chunks = [invoices[i:i+1000] for i in range(0, len(invoices), 1000)]
    logger.info(f"Split into {len(chunks)} batch(es) of up to 1000")
    
    all_results = {}
    original_requests_by_custom_id = {}
    
    for chunk_idx, chunk in enumerate(chunks):
        logger.info(f"Processing chunk {chunk_idx+1}/{len(chunks)}...")
        
        # ── Step 3: Build batch requests ───────────────────────────────────
        batch_requests = []
        for i, invoice in enumerate(chunk):
            custom_id = f"chunk{chunk_idx:02d}-invoice-{i:04d}"
            prompt = build_invoice_extraction_prompt(invoice.text)
            
            params = {
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 400,
                "temperature": 0.0,
                "messages": [{"role": "user", "content": prompt}],
            }
            
            original_requests_by_custom_id[custom_id] = params
            
            batch_requests.append(
                anthropic.types.message_create_params.Request(
                    custom_id=custom_id,
                    params=anthropic.types.MessageCreateParamsNonStreaming(**params),
                )
            )
        
        # ── Step 4: Submit batch ────────────────────────────────────────────
        batch = client.beta.messages.batches.create(requests=batch_requests)
        logger.info(f"Batch {batch.id} submitted ({len(batch_requests)} requests)")
        
        # ── Step 5: Poll for completion ─────────────────────────────────────
        status = await poll_batch_async(
            batch.id,
            initial_interval=60.0,
            max_interval=poll_interval,
            timeout_hours=max_wait_hours,
            progress_callback=lambda c: logger.debug(
                f"  ✅{c.succeeded} ❌{c.errored} ⏳{c.processing}"
            ),
        )
        
        if status != "ended":
            logger.error(f"Batch ended with unexpected status: {status}")
            continue
        
        # ── Step 6: Collect results ─────────────────────────────────────────
        chunk_results = collect_batch_results(batch.id)
        all_results.update(chunk_results)
    
    # ── Step 7: Retry loop ──────────────────────────────────────────────────
    for retry_attempt in range(max_retries):
        analysis = analyse_batch_failures(all_results)
        
        if not analysis.retryable and not analysis.parse_errors:
            break  # Nothing to retry
        
        logger.info(
            f"Retry {retry_attempt+1}/{max_retries}: "
            f"{len(analysis.retryable)} errors, {len(analysis.parse_errors)} parse failures"
        )
        
        retry_ids = analysis.retryable + analysis.parse_errors
        retry_batch_id = resubmit_failed_requests(
            original_requests_by_custom_id,
            retry_ids,
            stricter_prompt=(len(analysis.parse_errors) > 0),
        )
        
        await poll_batch_async(retry_batch_id, initial_interval=30.0, timeout_hours=2.0)
        retry_results = collect_batch_results(retry_batch_id)
        all_results = merge_batch_results(all_results, retry_results)
    
    # ── Step 8: Process successes ───────────────────────────────────────────
    for custom_id, result in all_results.items():
        if result["status"] == "success" and result.get("is_json") != False:
            invoice_data = result["data"]
            chunk_idx_str, _, invoice_idx_str = custom_id.split("-")[0:3]
            chunk_idx = int(chunk_idx_str.replace("chunk", ""))
            invoice_idx = int(invoice_idx_str)
            
            original_invoice = chunks[chunk_idx][invoice_idx]
            await save_extracted_invoice_to_db(original_invoice, invoice_data)
            total_succeeded += 1
        else:
            total_failed += 1
    
    # ── Step 9: Alert on failures ────────────────────────────────────────────
    if total_failed > 0:
        failure_rate = total_failed / (total_succeeded + total_failed) * 100
        if failure_rate > 5.0:  # Alert if >5% failure rate
            await send_ops_alert(
                f"⚠️ Invoice pipeline failure rate: {failure_rate:.1f}% "
                f"({total_failed}/{total_succeeded + total_failed} invoices)"
            )
    
    # ── Step 10: Calculate cost ──────────────────────────────────────────────
    total_tokens = sum(
        r.get("tokens", 0) for r in all_results.values() if r["status"] == "success"
    )
    cost = calculate_batch_cost(total_tokens, model="claude-haiku-4-5-20251001")
    
    elapsed = (datetime.utcnow() - pipeline_start).seconds
    logger.info(
        f"✅ Pipeline complete in {elapsed}s: "
        f"{total_succeeded} succeeded, {total_failed} failed, "
        f"${cost:.4f} batch cost"
    )
    
    return {"succeeded": total_succeeded, "failed": total_failed, "cost_usd": cost}


def build_invoice_extraction_prompt(invoice_text: str) -> str:
    return f"""Extract data from this supplier invoice. Return only a JSON object.

Required fields:
{{
  "vendor_name": "string",
  "invoice_number": "string",
  "invoice_date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD or null",
  "total_amount": number,
  "subtotal": number,
  "tax_amount": number,
  "currency": "ISO 4217 code",
  "line_items": [
    {{
      "description": "string",
      "quantity": number,
      "unit_price": number,
      "total": number
    }}
  ],
  "notes": "string or null"
}}

Invoice:
{invoice_text}"""
```

---

## 9. Cost Comparison and ROI

### Batch vs Sync Cost Calculator

```python
from dataclasses import dataclass

@dataclass
class BatchCostAnalysis:
    sync_cost_usd: float
    batch_cost_usd: float
    savings_usd: float
    savings_pct: float
    monthly_sync_usd: float
    monthly_batch_usd: float
    monthly_savings_usd: float
    annual_savings_usd: float


# 2026 pricing (per million tokens)
PRICING_PER_MTK = {
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-6":         {"input": 3.00, "output": 15.00},
    "claude-opus-4-6":           {"input": 15.00, "output": 75.00},
}

# Batch discount is 50% off all prices
BATCH_DISCOUNT = 0.50


def calculate_batch_savings(
    n_requests: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
    model: str = "claude-haiku-4-5-20251001",
    jobs_per_day: int = 1,
) -> BatchCostAnalysis:
    """
    Calculate exact cost savings from using Batch API.
    
    Example - Lumière nightly invoice processing:
        n_requests=500, avg_input=800, avg_output=200, model=haiku
        → sync: $0.042/night  → batch: $0.021/night  → $7.67/year savings
    
    Example - Monthly menu rewrite (Sonnet):
        n_requests=300, avg_input=400, avg_output=150, model=sonnet
        → sync: $0.43/month  → batch: $0.21/month  → $2.52/year savings
    """
    prices = PRICING_PER_MTK[model]
    
    # Calculate per-run costs
    sync_input_cost  = n_requests * avg_input_tokens  / 1_000_000 * prices["input"]
    sync_output_cost = n_requests * avg_output_tokens / 1_000_000 * prices["output"]
    sync_cost = sync_input_cost + sync_output_cost
    batch_cost = sync_cost * BATCH_DISCOUNT
    
    # Monthly/annual projections
    monthly_runs = jobs_per_day * 30
    monthly_sync  = sync_cost  * monthly_runs
    monthly_batch = batch_cost * monthly_runs
    
    return BatchCostAnalysis(
        sync_cost_usd=round(sync_cost, 6),
        batch_cost_usd=round(batch_cost, 6),
        savings_usd=round(sync_cost - batch_cost, 6),
        savings_pct=50.0,
        monthly_sync_usd=round(monthly_sync, 4),
        monthly_batch_usd=round(monthly_batch, 4),
        monthly_savings_usd=round(monthly_sync - monthly_batch, 4),
        annual_savings_usd=round((monthly_sync - monthly_batch) * 12, 2),
    )


def print_batch_roi_report(
    workloads: list[dict],  # List of {"name": ..., "n_requests": ..., ...}
):
    """Print a formatted ROI comparison table for multiple workloads."""
    print(f"\n{'Workload':<30} {'Sync/run':>10} {'Batch/run':>10} {'Savings':>8} {'Annual':>12}")
    print("-" * 75)
    
    total_annual_savings = 0
    
    for w in workloads:
        analysis = calculate_batch_savings(**{k: v for k, v in w.items() if k != "name"})
        print(
            f"{w['name']:<30} "
            f"${analysis.sync_cost_usd:>9.4f} "
            f"${analysis.batch_cost_usd:>9.4f} "
            f"  50.0% "
            f"${analysis.annual_savings_usd:>11.2f}"
        )
        total_annual_savings += analysis.annual_savings_usd
    
    print("-" * 75)
    print(f"{'TOTAL ANNUAL SAVINGS':<62} ${total_annual_savings:>11.2f}")


# Lumière restaurant batch workloads
LUMIERE_BATCH_WORKLOADS = [
    {"name": "Nightly invoice processing",  "n_requests": 500,  "avg_input_tokens": 800,  "avg_output_tokens": 200, "model": "claude-haiku-4-5-20251001", "jobs_per_day": 1},
    {"name": "Daily review classification", "n_requests": 50,   "avg_input_tokens": 200,  "avg_output_tokens": 5,   "model": "claude-haiku-4-5-20251001", "jobs_per_day": 1},
    {"name": "Weekly menu rewrites",        "n_requests": 80,   "avg_input_tokens": 400,  "avg_output_tokens": 150, "model": "claude-sonnet-4-6",         "jobs_per_day": 1/7},
    {"name": "Monthly guest reports",       "n_requests": 200,  "avg_input_tokens": 1200, "avg_output_tokens": 600, "model": "claude-sonnet-4-6",         "jobs_per_day": 1/30},
]

# print_batch_roi_report(LUMIERE_BATCH_WORKLOADS)
# Output:
# Workload                        Sync/run  Batch/run  Savings       Annual
# ---------------------------------------------------------------------------
# Nightly invoice processing       $0.0416   $0.0208   50.0%       $76.12
# Daily review classification      $0.0001   $0.0001   50.0%        $0.18
# Weekly menu rewrites             $0.0210   $0.0105   50.0%       $36.47
# Monthly guest reports            $0.1080   $0.0540   50.0%       $64.80
# ---------------------------------------------------------------------------
# TOTAL ANNUAL SAVINGS                                             $177.57


def calculate_batch_cost(total_tokens: int, model: str) -> float:
    """Estimate cost from total token count (input + output combined)."""
    avg_price = (PRICING_PER_MTK[model]["input"] + PRICING_PER_MTK[model]["output"]) / 2
    return total_tokens / 1_000_000 * avg_price * BATCH_DISCOUNT
```

---

## 10. Batch API with Prompt Caching

Combine Batch API (50% discount) with Prompt Caching (90% discount on cache reads) for maximum savings.

```python
def create_cached_batch(
    items: list[str],
    stable_system_prompt: str,         # Must be >1024 tokens to qualify for caching
    task_template: str,
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 300,
) -> str:
    """
    Create a batch where the system prompt is cache-enabled.
    
    Cost breakdown per request (after first):
        - System prompt tokens:  0.10× (cache read, 90% discount)
        - Task-specific tokens:  0.40× (batch write, 50% discount from batch)
    
    This is the cheapest possible configuration for high-volume batch work.
    
    Requirements:
        - stable_system_prompt must be >= 1024 tokens
        - Items in the batch should share the same system prompt
        - Cache TTL is 5 minutes but batch jobs are processed asynchronously
          so caching is most effective when requests are processed sequentially
    """
    requests = []
    
    for i, item in enumerate(items):
        requests.append(
            anthropic.types.message_create_params.Request(
                custom_id=f"item-{i:05d}",
                params=anthropic.types.MessageCreateParamsNonStreaming(
                    model=model,
                    max_tokens=max_tokens,
                    system=[
                        {
                            "type": "text",
                            "text": stable_system_prompt,
                            "cache_control": {"type": "ephemeral"},
                            # This marks the system prompt as cacheable
                            # First request: cache_write (1.25× cost)
                            # Subsequent: cache_read (0.10× cost)
                        }
                    ],
                    messages=[{
                        "role": "user",
                        "content": task_template.format(item=item),
                    }],
                    betas=["prompt-caching-2024-07-31"],  # Enable caching
                )
            )
        )
    
    batch = client.beta.messages.batches.create(requests=requests)
    return batch.id


# Example system prompt for Lumière (must be >1024 tokens for caching to apply)
LUMIERE_EXTRACTION_SYSTEM = """
You are a data extraction specialist for Lumière, an award-winning fine dining restaurant 
in London's Mayfair district. The restaurant has been operating since 1987 and is known for 
its exceptional French-British fusion cuisine, extensive wine cellar of 2,400 labels, and 
impeccable service standards.

Your task is to extract structured data from restaurant documents with complete accuracy.
All financial figures must be in the exact format specified — never round or approximate.
Dates must be in YYYY-MM-DD format unless specified otherwise.
Vendor names must be exactly as they appear in the document.

EXTRACTION RULES:
1. Return only valid JSON — no preamble, no explanation, no markdown code blocks
2. If a field is not present in the document, use null (not empty string, not "N/A")
3. All monetary values should be numbers (not strings) without currency symbols
4. Currency codes must be ISO 4217 (USD, GBP, EUR, JPY, etc.)
5. If you detect ambiguity, add a "notes" field with your observation
6. Line items should preserve all detail from the original document
7. Never infer or calculate values — only extract what's explicitly stated

QUALITY STANDARDS:
- Accuracy is critical — these extractions are used for financial reconciliation
- Duplicate line items are possible in source data — preserve all duplicates
- Multi-page invoices may have subtotals — capture the final total only
- Tax may be listed as VAT, GST, HST, or other regional names — normalize to "tax"

ERROR HANDLING:
- If the document appears to be non-financial (e.g., a letter), return: {"error": "not_an_invoice", "document_type": "your guess"}
- If critical fields (vendor, date, total) are missing, still extract what's available and note missing fields

You have processed thousands of invoices from the following regular Lumière vendors:
- Berry Bros & Rudd (wine supplier)
- Rungis International (produce)
- The Meat Hook (meats)
- La Fromagerie (cheese)
- Nespresso Professional (beverages)
- Electrolux Professional (equipment maintenance)
- Linen & Things (table linens)
""" * 1  # This is approximately 350 tokens — you'd need more content for >1024 token threshold
```

---

## 11. Azure-Integrated Batch Pipeline

### Azure Functions + Blob Storage Trigger

```python
# Azure Function: triggered nightly by Azure Scheduler
import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
import logging

app = func.FunctionApp()

@app.schedule(schedule="0 0 2 * * *", arg_name="timer", run_on_startup=False)
async def nightly_batch_trigger(timer: func.TimerRequest) -> None:
    """Run at 02:00 UTC every night."""
    logging.info("Nightly batch pipeline triggered")
    
    result = await nightly_invoice_pipeline()
    
    # Save result to Table Storage for monitoring
    await save_pipeline_result(result)
    
    logging.info(f"Pipeline complete: {result}")


async def load_new_invoices_from_blob(container: str = "invoices-incoming") -> list:
    """
    Load unprocessed invoices from Azure Blob Storage.
    Marks processed invoices by moving to 'invoices-processed' container.
    """
    credential = DefaultAzureCredential()
    blob_service = BlobServiceClient(
        account_url="https://lumierrestorage.blob.core.windows.net",
        credential=credential
    )
    
    container_client = blob_service.get_container_client(container)
    invoices = []
    
    async for blob in container_client.list_blobs():
        if blob.name.endswith(".txt") or blob.name.endswith(".pdf"):
            blob_client = container_client.get_blob_client(blob.name)
            content = await blob_client.download_blob()
            text = await content.readall()
            invoices.append({
                "name": blob.name,
                "text": text.decode("utf-8", errors="ignore"),
                "blob_client": blob_client,
            })
    
    return invoices


async def save_extracted_invoice_to_db(invoice: dict, extracted_data: dict):
    """Save extracted invoice data to Azure SQL Database."""
    import aioodbc
    
    dsn = (
        "Driver={ODBC Driver 18 for SQL Server};"
        "Server=lumiere-sql.database.windows.net;"
        "Database=LumiereOps;"
        "Authentication=ActiveDirectoryMsi"
    )
    
    async with aioodbc.connect(dsn=dsn) as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO Invoices (
                    vendor_name, invoice_date, total_amount, currency,
                    raw_data, processed_at
                ) VALUES (?, ?, ?, ?, ?, GETUTCDATE())
            """, (
                extracted_data.get("vendor_name"),
                extracted_data.get("invoice_date"),
                extracted_data.get("total_amount"),
                extracted_data.get("currency"),
                json.dumps(extracted_data),
            ))
            await conn.commit()
    
    # Move blob to processed container
    await move_blob_to_processed(invoice["blob_client"])


async def move_blob_to_processed(source_blob_client):
    """Move a processed invoice blob to the archive container."""
    dest_url = source_blob_client.url.replace(
        "/invoices-incoming/", "/invoices-processed/"
    )
    await source_blob_client.start_copy_from_url(dest_url)
    await source_blob_client.delete_blob()
```

---

## 12. Monitoring and Alerting

### Application Insights Integration

```python
from applicationinsights import TelemetryClient

tc = TelemetryClient(instrumentation_key="YOUR_AI_KEY")

def track_batch_metrics(batch_id: str, results: dict, cost_usd: float):
    """Send batch pipeline metrics to Application Insights."""
    
    succeeded = sum(1 for r in results.values() if r["status"] == "success")
    failed = sum(1 for r in results.values() if r["status"] == "error")
    parse_errors = sum(1 for r in results.values() if r["status"] == "parse_error")
    total = len(results)
    
    # Track as custom event
    tc.track_event("BatchPipelineCompleted", {
        "batch_id": batch_id,
        "succeeded": str(succeeded),
        "failed": str(failed),
        "parse_errors": str(parse_errors),
        "success_rate": str(succeeded / total * 100 if total else 0),
    })
    
    # Track metrics for dashboards
    tc.track_metric("batch_success_rate",   succeeded / total * 100 if total else 0)
    tc.track_metric("batch_failure_count",  failed)
    tc.track_metric("batch_cost_usd",       cost_usd)
    tc.track_metric("batch_total_requests", total)
    
    tc.flush()


# KQL Queries for Azure Monitor Dashboard:
KQL_BATCH_METRICS = """
// Daily batch success rates
customEvents
| where name == "BatchPipelineCompleted"
| extend 
    success_rate = todouble(customDimensions["success_rate"]),
    total = toint(customDimensions["succeeded"]) + toint(customDimensions["failed"])
| summarize
    avg_success_rate = avg(success_rate),
    total_processed = sum(total)
    by bin(timestamp, 1d)
| order by timestamp desc

// Monthly cost trend
customMetrics
| where name == "batch_cost_usd"
| summarize monthly_cost = sum(value) by bin(timestamp, 30d)
| order by timestamp desc
"""
```

---

## 13. Junior Developer Walkthrough

**Goal**: Process 100 restaurant reviews overnight, classify sentiment.

### Step 1: Set Up

```python
import anthropic
import json

client = anthropic.Anthropic()  # Reads ANTHROPIC_API_KEY from env

# Your 100 reviews
reviews = [
    "The duck confit was absolutely transcendent. Service impeccable.",
    "Waited 45 minutes for main course. Won't return.",
    "Average food, exceptional wine list. Mixed experience.",
    # ... 97 more
]
```

### Step 2: Create the Batch

```python
# Build batch requests
requests = []
for i, review in enumerate(reviews):
    requests.append(
        anthropic.types.message_create_params.Request(
            custom_id=f"review-{i:03d}",          # "review-000" to "review-099"
            params=anthropic.types.MessageCreateParamsNonStreaming(
                model="claude-haiku-4-5-20251001", # Cheapest — simple classification
                max_tokens=10,                     # "positive", "negative", "neutral"
                messages=[{
                    "role": "user",
                    "content": f"Classify the sentiment of this restaurant review.\nReturn only: positive, negative, or neutral.\n\nReview: {review}"
                }],
            )
        )
    )

# Submit the batch
batch = client.beta.messages.batches.create(requests=requests)
batch_id = batch.id
print(f"Batch submitted: {batch_id}")
print(f"Save this ID! You'll need it to get results: {batch_id}")
```

### Step 3: Wait and Check

```python
# Wait for completion (check every 60 seconds)
import time

while True:
    batch = client.beta.messages.batches.retrieve(batch_id)
    counts = batch.request_counts
    print(f"Status: {batch.processing_status} | Done: {counts.succeeded} | Pending: {counts.processing}")
    
    if batch.processing_status == "ended":
        break
    
    time.sleep(60)  # Wait 1 minute between checks

print("Batch complete!")
```

### Step 4: Get Results

```python
# Collect all results
results = {}
for result in client.beta.messages.batches.results(batch_id):
    if result.result.type == "succeeded":
        sentiment = result.result.message.content[0].text.strip().lower()
        results[result.custom_id] = sentiment
    else:
        results[result.custom_id] = "error"

# Print summary
from collections import Counter
sentiment_counts = Counter(results.values())
print(f"Results: {dict(sentiment_counts)}")
# Output: {'positive': 67, 'negative': 24, 'neutral': 9}
```

---

## 14. Senior Developer Patterns

### Pattern 1: Idempotent Batch Pipeline

```python
class IdempotentBatchPipeline:
    """
    Pipeline that safely handles restarts and duplicate runs.
    If the pipeline is interrupted and restarted, it picks up where it left off
    rather than submitting duplicate batches.
    """
    
    def __init__(self, pipeline_name: str, state_file: str = "pipeline_state.json"):
        self.name = pipeline_name
        self.state_file = Path(state_file)
        self.state = self._load_state()
    
    def _load_state(self) -> dict:
        if self.state_file.exists():
            return json.loads(self.state_file.read_text())
        return {}
    
    def _save_state(self):
        self.state_file.write_text(json.dumps(self.state, indent=2))
    
    async def run(self, items: list, force_restart: bool = False) -> dict:
        run_key = f"{self.name}_{datetime.utcnow().strftime('%Y%m%d')}"
        
        if run_key in self.state and not force_restart:
            existing = self.state[run_key]
            if existing.get("status") == "completed":
                print(f"⏭️  Skipping {run_key} — already completed")
                return existing["results"]
            elif existing.get("batch_id"):
                print(f"⟳  Resuming {run_key} — batch already submitted")
                batch_id = existing["batch_id"]
            else:
                batch_id = None
        else:
            batch_id = None
        
        # Submit if not already submitted
        if not batch_id:
            batch_id = self._submit_batch(items)
            self.state[run_key] = {"batch_id": batch_id, "status": "submitted"}
            self._save_state()
        
        # Poll
        await poll_batch_async(batch_id)
        
        # Collect
        results = collect_batch_results(batch_id)
        
        # Save completed state
        self.state[run_key] = {"batch_id": batch_id, "status": "completed", "results": results}
        self._save_state()
        
        return results
```

### Pattern 2: Progressive Batch with Early Results

```python
async def progressive_batch_results(batch_id: str, on_result_callback):
    """
    Process results as they arrive rather than waiting for all to complete.
    Use for large batches where you want to start downstream processing early.
    
    Warning: Batch API doesn't stream partial results — you see all results
    only after status=="ended". This pattern polls and processes the full
    result set immediately upon completion.
    """
    await poll_batch_async(batch_id, initial_interval=30.0)
    
    processed_ids = set()
    
    for result in client.beta.messages.batches.results(batch_id):
        if result.custom_id not in processed_ids:
            processed_ids.add(result.custom_id)
            await on_result_callback(result)
```

---

## 15. Tips, Tricks, and Gotchas

### ✅ Do's

**Always save the batch_id to durable storage immediately after creation.**  
Your process could restart, your Lambda could time out, your Azure Function could stop. If you lose the batch_id, you can call `client.beta.messages.batches.list()` to find recent batches, but it's much cleaner to have it saved.

**Use zero-padded custom_ids for easy sorting**: `f"item-{i:05d}"` not `f"item-{i}"`.  
Sorting `item-00001` through `item-09999` works correctly; sorting `item-1` through `item-9999` does not.

**Set `temperature=0.0` for extraction tasks**.  
You want deterministic, consistent output. Temperature introduces variance that makes JSON parsing harder.

**Keep max_tokens tight** — for yes/no: 5, classification: 15, extraction: 300-500, short text: 200.  
Haiku at 300 max_tokens is significantly cheaper than Haiku at 2048.

**Test with 10 requests before submitting 10,000**.  
Validate your prompts, custom_id scheme, and result parsing on a tiny batch first.

### ❌ Don'ts

**Don't poll faster than every 10 seconds**.  
Polling too fast consumes your rate limit budget and is unnecessary — Anthropic processes batches at their own rate.

**Don't assume all results are JSON**.  
Even when you ask for JSON, occasional responses may have preamble or be wrapped in markdown. Always use `extract_json_from_response()` rather than raw `json.loads()`.

**Don't submit a new batch if one is already running for the same job**.  
Use idempotency keys or check `list_active_batches()` before submitting. Duplicate batches = double cost.

**Don't use Batch API for anything requiring < 1 minute response time**.  
Even small batches can take 5-30 minutes. If a user is waiting, use sync.

**Don't ignore the `expired` status**.  
Batches expire after 24 hours if not processed. Check `request_counts.expired` and handle accordingly.

### 🔧 Gotchas

**Batch results are available for 29 days** after completion. After that, they're deleted. Always collect and store results promptly.

**Prompt caching within batches**: requests in the same batch share cache if they have identical cacheable blocks. But the 5-minute TTL means caching is only effective if requests are processed close together — which they may not be for large batches.

**Error type `"overloaded"` is retryable** even in batch mode. Include it in your retry logic.

**Canceled batches may have partial results** — requests processed before cancellation are still available via `collect_batch_results()`.

**Custom IDs must be unique within a batch** — duplicate custom_ids cause request rejection.

---

## 16. Quick Reference Cheatsheet

```python
# ── SUBMIT ─────────────────────────────────────────────────────────────────
batch = client.beta.messages.batches.create(requests=[
    anthropic.types.message_create_params.Request(
        custom_id="item-00001",
        params=anthropic.types.MessageCreateParamsNonStreaming(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": "Your prompt here"}],
        )
    )
    # ... up to 10,000 requests
])
batch_id = batch.id  # SAVE THIS!

# ── POLL ────────────────────────────────────────────────────────────────────
batch = client.beta.messages.batches.retrieve(batch_id)
batch.processing_status  # "in_progress" | "ended" | "canceling" | "canceled"
batch.request_counts.succeeded   # Completed successfully
batch.request_counts.errored     # Failed with error
batch.request_counts.processing  # Still running

# ── COLLECT ─────────────────────────────────────────────────────────────────
for result in client.beta.messages.batches.results(batch_id):
    result.custom_id            # Your ID
    result.result.type          # "succeeded" | "errored"
    if result.result.type == "succeeded":
        result.result.message.content[0].text  # Response text
        result.result.message.usage.input_tokens
        result.result.message.usage.output_tokens

# ── CANCEL ──────────────────────────────────────────────────────────────────
client.beta.messages.batches.cancel(batch_id)

# ── LIST ────────────────────────────────────────────────────────────────────
for batch in client.beta.messages.batches.list():
    print(batch.id, batch.processing_status)

# ── COST ────────────────────────────────────────────────────────────────────
# Batch = 50% of sync price
# claude-haiku:  $0.40/$2.00 input/output per MTok (batch price)
# claude-sonnet: $1.50/$7.50 input/output per MTok (batch price)
# claude-opus:   $7.50/$37.50 input/output per MTok (batch price)

# ── LIMITS ──────────────────────────────────────────────────────────────────
# Max requests per batch: 10,000
# Batch expires after:    24 hours
# Results available for:  29 days
# Min poll interval:      10 seconds
```
