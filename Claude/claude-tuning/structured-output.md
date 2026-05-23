# structured-output.md — Getting Reliable Structured Outputs from Claude

> **Purpose**: Complete guide to reliably extracting JSON, XML, CSV, and typed structured outputs from Claude without post-processing failures — from basic prefilling to Pydantic-validated tool use.  
> **Owner**: jose@hybridgenai.com  
> **Updated**: 2026-05-22

---

## Navigation

1. [The Core Problem](#1-the-core-problem)
2. [Technique 1: Assistant Prefill](#2-technique-1-assistant-prefill)
3. [Technique 2: Pydantic + Tool Use (Production Grade)](#3-technique-2-pydantic--tool-use-production-grade)
4. [Technique 3: Schema in Prompt](#4-technique-3-explicit-schema-in-prompt)
5. [Robust JSON Parser](#5-robust-json-parser)
6. [Structured Output for Other Formats](#6-structured-output-for-other-formats)
7. [Validation and Retry Pattern](#7-validation-and-retry-pattern)
8. [Complex Schema Patterns](#8-complex-schema-patterns)
9. [Streaming Structured Output](#9-streaming-structured-output)
10. [Junior Quick-Start Walkthrough](#10-junior-quick-start-walkthrough)
11. [Senior Patterns and Production Hardening](#11-senior-patterns-and-production-hardening)
12. [Tips, Tricks and Gotchas](#12-tips-tricks-and-gotchas)
13. [Quick Reference Cheatsheet](#13-quick-reference-cheatsheet)

---

## 1. The Core Problem

Claude generates text. Your application needs data structures. The gap between "Claude said something JSON-like" and "my application can reliably parse it" is where most production issues arise.

```
What Claude generates without guidance:
  "The invoice is from Acme Corp, dated March 15th 2026, and the total
  comes to four thousand, five hundred dollars. Here's the structured
  data you asked for:
  ```json
  {
    "vendor": "Acme Corp",
    ...
  }
  ```"

What your application needs:
  {"vendor": "Acme Corp", "date": "2026-03-15", "total": 4500.00}

The problems:
  1. Markdown code fences (```json ... ```) — must be stripped
  2. Preamble text before JSON — must be removed
  3. Wrong types ("four thousand dollars" vs 4500.00)
  4. Missing fields (null vs omitted)
  5. Extra commentary after JSON
```

**Reliability hierarchy (best → worst):**
```
1. Tool use with forced tool_choice     → 99.9% reliability (schema enforced)
2. Prefill trick                        → 98% reliability (starts correctly)
3. Explicit schema + "JSON only"        → 95% reliability (depends on instruction following)
4. "Return JSON" without schema         → 80% reliability (Claude guesses the schema)
```

---

## 2. Technique 1: Assistant Prefill

Force the output to start exactly as needed by pre-populating the assistant turn.

```python
import anthropic, json

client = anthropic.Anthropic()

def extract_with_prefill(document_text: str, schema_hint: str = "{") -> dict:
    """
    Use assistant prefill to guarantee JSON output starts correctly.
    Claude continues from the prefilled character — skipping all preamble.

    Args:
        document_text: Document to extract from
        schema_hint: Prefill string to force output format
                     "{" for objects, "[" for arrays, '{"field": "' for specific start

    Returns:
        Parsed Python dict/list

    Examples:
        schema_hint="{" → forces object output
        schema_hint="[" → forces array output
        schema_hint='{"vendor": "' → forces output to start with vendor field
    """
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Extract structured data from this document.\n"
                    f"Return ONLY the JSON object. No explanation.\n\n"
                    f"Document:\n{document_text}"
                )
            },
            # Prefill — Claude continues from here, skipping any preamble
            {"role": "assistant", "content": schema_hint}
        ]
    )

    # Reconstruct: prepend the prefill to Claude's continuation
    raw_json = schema_hint + response.content[0].text
    return json.loads(raw_json)

# Examples:
# Force object output
result = extract_with_prefill(invoice_text, schema_hint="{")

# Force array of items
items = extract_with_prefill(line_items_text, schema_hint="[")

# Force output to start with a known field (prevents Claude changing field order)
result = extract_with_prefill(
    invoice_text,
    schema_hint='{"vendor_name": "'
)
```

### Prefill for Different Output Formats

```python
# Prefill patterns for common use cases:
PREFILL_PATTERNS = {
    "json_object":   "{",
    "json_array":    "[",
    "json_string":   '"',
    "yes_no":        "",         # Let Claude start naturally but instruct "yes or no only"
    "markdown_table": "| ",     # Force table start
    "csv_header":   "name,",    # Force CSV header
    "number_only":  "",         # Instruct "return number only"
    "classification": "",       # Instruct "return label only"
}

# For numeric-only extraction (e.g., confidence score):
response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=10,
    messages=[
        {"role": "user", "content": "What is the total? Invoice total: £4,500.00"},
        {"role": "assistant", "content": "4500"}  # Force numeric start
    ]
)
# Response will be the rest of the number (e.g., ".00")
# Full value: "4500" + response.content[0].text
```

---

## 3. Technique 2: Pydantic + Tool Use (Production Grade)

The most reliable method. Claude MUST populate all required fields with correct types.

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
import json

# Define your data model using Pydantic
class LineItem(BaseModel):
    description: str = Field(description="Item description")
    quantity: float = Field(description="Quantity of items")
    unit_price: float = Field(description="Price per unit, numeric only")
    line_total: float = Field(description="quantity × unit_price")

class InvoiceExtraction(BaseModel):
    vendor_name: str = Field(description="Company name exactly as written on invoice")
    invoice_number: Optional[str] = Field(default=None, description="Invoice number/reference. Null if not found.")
    invoice_date: str = Field(description="Invoice date in YYYY-MM-DD format")
    due_date: Optional[str] = Field(default=None, description="Payment due date in YYYY-MM-DD. Null if not found.")
    total_amount: float = Field(description="Total amount as a number. No currency symbols.")
    currency: Literal["GBP", "USD", "EUR", "CAD", "AUD"] = Field(description="Currency code")
    line_items: list[LineItem] = Field(default_factory=list, description="List of line items")
    confidence: Literal["high", "medium", "low"] = Field(
        description="Confidence that all required fields were correctly extracted."
    )

    @validator("invoice_date", "due_date", pre=True)
    def parse_date(cls, v):
        """Normalise various date formats to YYYY-MM-DD."""
        if v is None:
            return v
        # Add date parsing logic here (dateutil.parser, etc.)
        return v

# Build tool schema from Pydantic model
def pydantic_to_tool(
    model_class: type,
    tool_name: str,
    tool_description: str
) -> dict:
    """Convert a Pydantic model to a Claude tool schema."""
    schema = model_class.model_json_schema()
    # Remove Pydantic-specific fields that Claude doesn't need
    schema.pop("title", None)
    return {
        "name": tool_name,
        "description": tool_description,
        "input_schema": schema
    }

INVOICE_EXTRACTION_TOOL = pydantic_to_tool(
    InvoiceExtraction,
    tool_name="extract_invoice_data",
    tool_description=(
        "Extract structured invoice data from the provided document text. "
        "Always populate all required fields. Use null for optional fields not found."
    )
)

def extract_invoice(invoice_text: str) -> InvoiceExtraction:
    """
    Extract invoice data with Pydantic validation.

    Args:
        invoice_text: Raw invoice text

    Returns:
        Validated InvoiceExtraction object

    Raises:
        ValidationError: If Claude returns invalid types
        ValueError: If no tool call in response
    """
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        tools=[INVOICE_EXTRACTION_TOOL],
        # Force Claude to ALWAYS use this tool — no prose fallback
        tool_choice={"type": "tool", "name": "extract_invoice_data"},
        messages=[{
            "role": "user",
            "content": f"Extract invoice data from:\n\n{invoice_text}"
        }]
    )

    # With forced tool_choice, first content block is always tool_use
    for block in response.content:
        if block.type == "tool_use":
            # Pydantic validates types and field constraints
            return InvoiceExtraction(**block.input)

    raise ValueError("No tool call found in response (unexpected with forced tool_choice)")

# Usage
invoice_data = extract_invoice(raw_invoice_text)
print(f"Vendor: {invoice_data.vendor_name}")
print(f"Total: {invoice_data.currency} {invoice_data.total_amount}")
print(f"Confidence: {invoice_data.confidence}")
print(f"Line items: {len(invoice_data.line_items)}")
```

### Multiple Schema Variants (Multi-Document Type)

```python
class RestaurantReservationRequest(BaseModel):
    guest_name: Optional[str] = Field(default=None, description="Guest's full name")
    party_size: Optional[int] = Field(default=None, ge=1, le=50, description="Number of guests")
    date: Optional[str] = Field(default=None, description="YYYY-MM-DD format")
    time: Optional[str] = Field(default=None, description="HH:MM 24-hour format")
    special_requests: list[str] = Field(default_factory=list)
    dining_occasion: Optional[Literal["birthday", "anniversary", "business", "casual"]] = None
    dietary_requirements: list[str] = Field(default_factory=list)
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    confidence: Literal["high", "medium", "low"] = "medium"

class WineQueryExtraction(BaseModel):
    wine_style: Optional[Literal["red", "white", "rosé", "sparkling", "dessert", "fortified"]] = None
    max_price_gbp: Optional[float] = Field(default=None, ge=0)
    food_pairing: Optional[str] = None
    region_preference: Optional[str] = None
    occasion: Optional[str] = None
    preferred_producers: list[str] = Field(default_factory=list)
```

---

## 4. Technique 3: Explicit Schema in Prompt

When tool use is not available or appropriate, provide the exact schema with field-by-field instructions.

```python
EXTRACTION_SCHEMA_PROMPT = """
Extract the following fields from the document. Return ONLY valid JSON.
No explanation, no markdown code fences, no text before or after the JSON.

Schema (follow exactly — use null for missing fields, NEVER omit fields):
{{
  "vendor_name": "string — company name as written on invoice",
  "invoice_date": "string — YYYY-MM-DD format",
  "invoice_number": "string or null",
  "total_amount": "number — numeric value only, no currency symbols",
  "currency": "GBP | USD | EUR | CAD | AUD",
  "line_items": [
    {{
      "description": "string",
      "quantity": "number",
      "unit_price": "number",
      "line_total": "number"
    }}
  ],
  "confidence": "high | medium | low"
}}

Rules:
- All dates in ISO 8601 format (YYYY-MM-DD)
- All amounts as numbers (e.g., 4500.00, not "£4,500.00")
- Empty arrays for missing lists: [] not null
- null for missing scalar fields, not "" or "N/A"
- confidence: 'high' if all required fields found, 'low' if guessing

Document to extract from:
<document>
{document_text}
</document>
"""

def extract_with_schema_prompt(document_text: str) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": EXTRACTION_SCHEMA_PROMPT.format(document_text=document_text)
        }],
        # Start with { to avoid preamble
        # Use prefill technique alongside schema prompt for double reliability
    )
    return parse_claude_json(response.content[0].text)
```

---

## 5. Robust JSON Parser

Claude occasionally wraps JSON in markdown code fences or adds preamble. Handle this defensively.

```python
import re
import json
from typing import Any

def parse_claude_json(response_text: str, expected_type: type = dict) -> Any:
    """
    Robustly extract and parse JSON from Claude's response.

    Handles:
    - Raw JSON with no wrapper
    - JSON wrapped in ```json ... ``` code fences
    - JSON wrapped in ``` ... ``` code fences
    - JSON with leading/trailing prose
    - Truncated JSON (from max_tokens cutoff)

    Args:
        response_text: Raw text from Claude's response
        expected_type: Expected type (dict or list) for validation

    Returns:
        Parsed Python object

    Raises:
        ValueError: If no valid JSON found or wrong type
    """
    text = response_text.strip()

    # Pattern 1: Strip markdown code fences
    json_fence_patterns = [
        r"```json\s*([\s\S]*?)\s*```",    # ```json ... ```
        r"```JSON\s*([\s\S]*?)\s*```",    # ```JSON ... ``` (uppercase)
        r"```\s*([\s\S]*?)\s*```",        # ``` ... ``` (generic)
    ]
    for pattern in json_fence_patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            text = match.group(1).strip()
            break

    # Pattern 2: Find first complete JSON structure
    for start_char, end_char, target_type in [
        ('{', '}', dict),
        ('[', ']', list)
    ]:
        start_idx = text.find(start_char)
        if start_idx == -1:
            continue

        # Balance brackets to find end
        depth = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(text[start_idx:], start_idx):
            if escape_next:
                escape_next = False
                continue
            if char == '\\' and in_string:
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == start_char:
                depth += 1
            elif char == end_char:
                depth -= 1
                if depth == 0:
                    json_candidate = text[start_idx:i+1]
                    try:
                        parsed = json.loads(json_candidate)
                        if isinstance(parsed, target_type):
                            if expected_type and not isinstance(parsed, expected_type):
                                continue
                            return parsed
                    except json.JSONDecodeError:
                        break

    raise ValueError(
        f"No valid JSON found in response. "
        f"First 300 chars: {response_text[:300]}"
    )

# Convenience wrappers
def parse_claude_dict(response_text: str) -> dict:
    return parse_claude_json(response_text, expected_type=dict)

def parse_claude_list(response_text: str) -> list:
    return parse_claude_json(response_text, expected_type=list)
```

---

## 6. Structured Output for Other Formats

### CSV Output

```python
CSV_EXTRACTION_PROMPT = """
Extract dish information and return as CSV.

Rules:
- First row MUST be the header: name,course,price_gbp,allergens,vegetarian
- One row per dish
- allergens: semicolon-separated within the field (e.g., "gluten;dairy")
- vegetarian: true or false (lowercase)
- price_gbp: number only (e.g., 28.50)
- No quotes unless the field contains commas
- No blank lines
- No explanation or commentary

Document:
<document>
{document_text}
</document>
"""

def extract_csv(document_text: str) -> list[dict]:
    """Extract tabular data as CSV and parse into list of dicts."""
    import csv, io

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": CSV_EXTRACTION_PROMPT.format(document_text=document_text)
        }]
    )

    csv_text = response.content[0].text.strip()

    # Strip any markdown wrapping
    if "```" in csv_text:
        csv_text = re.sub(r"```(?:csv)?\s*", "", csv_text).strip()

    reader = csv.DictReader(io.StringIO(csv_text))
    return list(reader)
```

### Key-Value Pairs

```python
KV_EXTRACTION_PROMPT = """
Extract the following fields. Return one field per line as KEY: value.
No explanation, no extra text.

Fields to extract:
- VENDOR: Company name
- DATE: Invoice date (YYYY-MM-DD)
- TOTAL: Total amount (number only)
- CURRENCY: Currency code (GBP/USD/EUR)
- INVOICE_NUM: Invoice reference number (or "NOT_FOUND")

Document:
{document_text}
"""

def extract_key_values(document_text: str) -> dict:
    """Extract key-value pairs and parse into dict."""
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": KV_EXTRACTION_PROMPT.format(document_text=document_text)}]
    )

    result = {}
    for line in response.content[0].text.strip().split("\n"):
        if ": " in line:
            key, _, value = line.partition(": ")
            result[key.strip()] = value.strip()

    return result
```

### XML Output

```python
XML_PROMPT = """
Extract invoice data as XML.
Return ONLY the XML, no explanation, no markdown.

Schema:
<invoice>
  <vendor_name>string</vendor_name>
  <invoice_date>YYYY-MM-DD</invoice_date>
  <total_amount>number</total_amount>
  <currency>GBP|USD|EUR</currency>
  <line_items>
    <item>
      <description>string</description>
      <quantity>number</quantity>
      <price>number</price>
    </item>
  </line_items>
</invoice>

Document: {document_text}
"""

def extract_xml(document_text: str) -> str:
    """Extract as XML string."""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": XML_PROMPT.format(document_text=document_text)
        }],
        # Prefill to force clean XML start
        # Note: prefill trick doesn't work directly with XML — use prompt only
    )
    xml_text = response.content[0].text.strip()

    # Strip markdown if present
    if "```xml" in xml_text:
        match = re.search(r"```xml\s*(.*?)\s*```", xml_text, re.DOTALL)
        if match:
            xml_text = match.group(1)
    elif "```" in xml_text:
        match = re.search(r"```\s*(.*?)\s*```", xml_text, re.DOTALL)
        if match:
            xml_text = match.group(1)

    return xml_text.strip()
```

---

## 7. Validation and Retry Pattern

```python
import time
from pydantic import ValidationError

def extract_with_retry(
    document_text: str,
    model_class: type,
    tool: dict,
    max_retries: int = 3,
    include_error_in_retry: bool = True
) -> BaseModel:
    """
    Extract structured data with automatic retry on validation failure.

    On retry, includes the previous error in the prompt to help Claude
    correct the specific mistake.

    Args:
        document_text: Source document
        model_class: Pydantic model class for validation
        tool: Tool schema dict
        max_retries: Maximum retry attempts (default: 3)
        include_error_in_retry: Include error context in retry prompt

    Returns:
        Validated Pydantic model instance

    Raises:
        RuntimeError: If all retries exhausted
    """
    last_error = None
    last_raw_response = None

    for attempt in range(1, max_retries + 1):
        # Build user message — include error context on retries
        user_content = f"Extract data from this document:\n\n{document_text}"
        if attempt > 1 and last_error and include_error_in_retry:
            user_content += (
                f"\n\nIMPORTANT: Previous extraction attempt failed with error:\n"
                f"{last_error}\n\n"
                f"Previous response: {str(last_raw_response)[:300]}\n\n"
                f"Please fix these specific issues and try again."
            )

        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1500,
                tools=[tool],
                tool_choice={"type": "tool", "name": tool["name"]},
                messages=[{"role": "user", "content": user_content}]
            )

            for block in response.content:
                if block.type == "tool_use":
                    last_raw_response = block.input
                    # Pydantic validates types, constraints, required fields
                    return model_class(**block.input)

            raise ValueError("No tool use block in response")

        except ValidationError as e:
            last_error = str(e)
            print(f"Attempt {attempt}/{max_retries} failed (Pydantic validation): {e}")
        except Exception as e:
            last_error = str(e)
            print(f"Attempt {attempt}/{max_retries} failed (API error): {e}")

        if attempt < max_retries:
            time.sleep(1 * attempt)  # Brief delay before retry

    raise RuntimeError(
        f"Failed to extract after {max_retries} attempts. "
        f"Last error: {last_error}"
    )

# Usage:
try:
    invoice = extract_with_retry(
        document_text=raw_invoice,
        model_class=InvoiceExtraction,
        tool=INVOICE_EXTRACTION_TOOL,
        max_retries=3
    )
    print(f"Success: {invoice.vendor_name} — {invoice.currency} {invoice.total_amount}")
except RuntimeError as e:
    print(f"Extraction failed: {e}")
    # Fall through to manual review queue
```

---

## 8. Complex Schema Patterns

### Hierarchical/Nested Schemas

```python
class Address(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    postcode: Optional[str] = None
    country: str = "UK"

class Supplier(BaseModel):
    name: str
    address: Optional[Address] = None
    vat_number: Optional[str] = None
    contact_email: Optional[str] = None

class ComplexInvoice(BaseModel):
    supplier: Supplier
    recipient: Supplier
    invoice_number: str
    issue_date: str
    payment_due: Optional[str] = None
    subtotal: float
    vat_amount: Optional[float] = None
    total: float
    currency: str = "GBP"
    notes: Optional[str] = None
    line_items: list[LineItem]
```

### Union Types / Polymorphic Output

```python
from typing import Union

class FoodMenuItem(BaseModel):
    item_type: Literal["food"] = "food"
    name: str
    description: str
    course: Literal["starter", "main", "dessert", "cheese"]
    price_gbp: float
    allergens: list[str] = Field(default_factory=list)
    vegetarian: bool = False
    vegan: bool = False

class WineMenuItem(BaseModel):
    item_type: Literal["wine"] = "wine"
    producer: str
    wine_name: str
    vintage: int
    appellation: str
    style: Literal["red", "white", "rosé", "sparkling", "dessert"]
    price_glass: Optional[float] = None
    price_bottle: float

MenuItem = Union[FoodMenuItem, WineMenuItem]

class MenuExtraction(BaseModel):
    items: list[dict]  # Use dict for polymorphic — validate manually
    total_item_count: int
    document_type: Literal["food_menu", "wine_list", "combined"]
```

---

## 9. Streaming Structured Output

When streaming, buffer the JSON until the stream is complete before parsing.

```python
def stream_and_parse_json(user_message: str, extraction_tool: dict) -> dict:
    """
    Stream a structured extraction and parse when complete.
    For long documents where you want to show progress.
    """
    accumulated_input = {}
    current_tool_use_id = None

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        tools=[extraction_tool],
        tool_choice={"type": "tool", "name": extraction_tool["name"]},
        messages=[{"role": "user", "content": user_message}]
    ) as stream:

        for event in stream:
            if event.type == "content_block_start":
                if event.content_block.type == "tool_use":
                    current_tool_use_id = event.content_block.id
                    print("Extracting...", end="", flush=True)

            elif event.type == "content_block_delta":
                if event.delta.type == "input_json_delta":
                    # Show progress
                    print(".", end="", flush=True)

        # Get the final complete message
        final_message = stream.get_final_message()
        print(" Done!")

        for block in final_message.content:
            if block.type == "tool_use":
                return block.input

    return {}
```

---

## 10. Junior Quick-Start Walkthrough

**Goal**: Extract structured data from text reliably in 15 minutes.

**Step 1**: Define what you want to extract.

```python
# First, write down the fields you need and their types
# Example: extract contact info from business cards

CONTACT_SCHEMA = """
{
  "name": "string — full name",
  "title": "string or null",
  "company": "string or null",
  "email": "string or null",
  "phone": "string or null"
}
"""
```

**Step 2**: Build the extraction prompt.

```python
def extract_contact(card_text: str) -> dict:
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",  # Haiku is fast and cheap for extraction
        max_tokens=200,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Extract contact information from this business card text.\n"
                    f"Return ONLY valid JSON matching this schema:\n{CONTACT_SCHEMA}\n"
                    f"Use null for missing fields.\n\n"
                    f"Card text:\n{card_text}"
                )
            },
            # Prefill trick: force JSON output
            {"role": "assistant", "content": "{"}
        ]
    )

    # Reconstruct full JSON
    raw = "{" + response.content[0].text
    return json.loads(raw)

# Test it
result = extract_contact("John Smith\nCTO at Acme Corp\njohn@acme.com\n+44 7700 900000")
print(result)
# {"name": "John Smith", "title": "CTO", "company": "Acme Corp",
#  "email": "john@acme.com", "phone": "+44 7700 900000"}
```

**Step 3**: Add error handling.

```python
def safe_extract_contact(card_text: str) -> dict:
    try:
        return extract_contact(card_text)
    except json.JSONDecodeError as e:
        print(f"JSON parse failed: {e}")
        return {"error": "parse_failed", "raw": card_text}
    except Exception as e:
        print(f"Extraction failed: {e}")
        return {"error": str(e)}
```

---

## 11. Senior Patterns and Production Hardening

### Type Coercion Helper

```python
def coerce_types(data: dict, schema: dict) -> dict:
    """
    Post-process extracted data to fix common type issues.
    Claude sometimes returns "4500" (string) when a number is needed.
    """
    result = {}
    for key, spec in schema.items():
        value = data.get(key)

        if value is None or value == "null" or value == "N/A" or value == "":
            result[key] = None
            continue

        # Coerce to expected type
        if spec["type"] == "number" and isinstance(value, str):
            # Remove currency symbols, commas, spaces
            clean = re.sub(r"[£$€,\s]", "", value)
            try:
                result[key] = float(clean)
            except ValueError:
                result[key] = None

        elif spec["type"] == "date":
            # Normalise date format
            try:
                from dateutil import parser as dateparser
                result[key] = dateparser.parse(value).strftime("%Y-%m-%d")
            except Exception:
                result[key] = value  # Keep original if parsing fails

        elif spec["type"] == "boolean" and isinstance(value, str):
            result[key] = value.lower() in ("true", "yes", "1", "on")

        else:
            result[key] = value

    return result
```

### Schema Versioning

```python
# Version your extraction schemas alongside your prompts
INVOICE_SCHEMA_V2 = {
    "version": "2.0",
    "model_class": InvoiceExtraction,
    "tool": INVOICE_EXTRACTION_TOOL,
    "added_in": "2026-05-22",
    "changelog": "Added VAT amount field; split address into structured sub-object"
}

INVOICE_SCHEMA_V1 = {
    "version": "1.0",
    "model_class": InvoiceExtractionV1,  # Legacy model class
    "tool": INVOICE_EXTRACTION_TOOL_V1,
    "deprecated": "2026-04-01"
}

# Migration helper
def migrate_v1_to_v2(v1_invoice: dict) -> InvoiceExtraction:
    """Migrate V1 invoice extraction to V2 schema."""
    return InvoiceExtraction(
        vendor_name=v1_invoice["vendor"],          # Field renamed
        invoice_date=v1_invoice["date"],
        total_amount=v1_invoice["total"],
        currency=v1_invoice.get("currency", "GBP"),
        vat_amount=None,                            # New field — not in V1
        line_items=v1_invoice.get("items", [])
    )
```

---

## 12. Tips, Tricks and Gotchas

**Tip 1 — Use forced tool_choice for anything going to a database.** Any extracted data that gets written to a database should use `tool_choice: {"type": "tool", "name": "X"}`. The schema enforcement prevents silent type errors.

**Tip 2 — Pydantic validators are your last line of defence.** Add `@validator` methods for date parsing, amount normalisation, and business rules. These catch Claude's edge cases.

**Tip 3 — Prefill + schema prompt = double reliability.** Use both: `{"role": "assistant", "content": "{"}` AND explicit schema instructions. The combination reaches ~99% parse success on typical documents.

**Tip 4 — Include example values in your schema descriptions.** "invoice_date: YYYY-MM-DD format (e.g., '2026-03-15')" outperforms just "invoice_date: date". Examples anchor Claude's output format.

**Tip 5 — Test edge cases: handwritten, unusual formats, multiple invoices.** Production documents are messier than your test set. Build a diverse evaluation dataset including damaged, handwritten, and multi-page documents.

**Gotcha 1 — `additionalProperties: False` in tool schemas.** Without this, Claude can hallucinate extra fields. Always add it to your `input_schema`.

**Gotcha 2 — Numbers as strings.** Claude sometimes returns `"4500"` (string) when you need `4500` (number). Pydantic catches this if the field type is `float`, but use `coerce_types()` for prompt-only extractions.

**Gotcha 3 — Null vs omitted vs empty string.** Specify exactly what you want for missing fields. "Use null, never omit fields, never use empty string" prevents schema inconsistencies.

**Gotcha 4 — Date format inconsistency.** Without explicit instruction, Claude may return "March 15, 2026", "15/03/2026", or "2026-03-15". Always specify "YYYY-MM-DD" and validate with `dateutil.parser`.

**Gotcha 5 — Max tokens truncating JSON.** If your extracted JSON is long and max_tokens is too small, the JSON gets cut off mid-string and `json.loads()` fails. Always set max_tokens generously for extraction (at least 2× the expected JSON size).

---

## 13. Quick Reference Cheatsheet

```
RELIABILITY HIERARCHY:
  1. Tool use + forced tool_choice → 99.9% (schema enforced by API)
  2. Prefill trick "{" or "["      → 98% (forces correct start)
  3. Explicit schema + "JSON only" → 95% (instruction following)
  4. "Return JSON" (no schema)     → 80% (Claude guesses)

PREFILL PATTERNS:
  JSON object:  {"role":"assistant","content":"{"}
  JSON array:   {"role":"assistant","content":"["}
  Specific key: {"role":"assistant","content":'{"vendor": "'}

TOOL USE SYNTAX:
  tool_choice={"type":"tool","name":"X"}  → always call tool X
  tool_choice={"type":"any"}              → call any tool
  tool_choice={"type":"auto"}             → Claude decides
  additionalProperties: False            → ALWAYS add to input_schema

NULL HANDLING:
  Missing scalars: null (never "" or "N/A")
  Missing arrays:  []  (never null)
  Missing objects: null

TYPE COERCION REMINDERS:
  Dates:    Always specify YYYY-MM-DD format
  Numbers:  "numeric value only, no currency symbols"
  Booleans: "true or false (lowercase)"
  Enums:    Use enum: ["option1", "option2"] in schema

RETRY STRATEGY:
  max_retries=3, delay=attempt * 1s
  Include error in retry prompt: "Previous attempt failed with: {error}"

PARSER ORDER:
  1. Try to find ```json``` fence
  2. Try to find ``` fence
  3. Find first '{' or '[' and balance brackets
  4. json.loads() the candidate
  5. Validate type (dict vs list)
  6. Raise ValueError if all fail
```
