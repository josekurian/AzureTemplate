# multimodal.md — Claude Vision and Multimodal Capabilities

> **Purpose**: Complete guide to using Claude's vision capabilities — image analysis, document processing, OCR, multi-image comparison, token cost management, and choosing between Claude Vision and Azure Document Intelligence.
> **Who This Is For**: Junior developers learning vision APIs; senior engineers building multimodal pipelines for food/beverage, document processing, and retail.
> **Owner**: jose@hybridgenai.com

---

## Navigation

1. [Supported Input Types and Limits](#1-supported-input-types-and-limits)
2. [Image Token Costs and Optimization](#2-image-token-costs-and-optimization)
3. [Basic Image Analysis (Base64)](#3-basic-image-analysis-base64)
4. [URL-Based Image Input](#4-url-based-image-input)
5. [Multi-Image Analysis and Comparison](#5-multi-image-analysis-and-comparison)
6. [Document OCR via Vision](#6-document-ocr-via-vision)
7. [Structured Output from Images](#7-structured-output-from-images)
8. [Vision vs Azure Document Intelligence](#8-vision-vs-azure-document-intelligence)
9. [Batch Image Processing](#9-batch-image-processing)
10. [Vision with Tool Use](#10-vision-with-tool-use)
11. [Junior Walkthrough — Analyse Your First Image](#11-junior-walkthrough--analyse-your-first-image)
12. [Senior Patterns — Production Vision Pipeline](#12-senior-patterns--production-vision-pipeline)
13. [Tips, Tricks, and Gotchas](#13-tips-tricks-and-gotchas)
14. [Quick Reference Cheatsheet](#14-quick-reference-cheatsheet)

---

## 1. Supported Input Types and Limits

```
┌─────────────────┬──────────────────────────────────┬───────────────────────────────┐
│ Input Type      │ Supported Formats                │ Limits                        │
├─────────────────┼──────────────────────────────────┼───────────────────────────────┤
│ Image (base64)  │ JPEG, PNG, GIF, WebP             │ 5MB per image, 20 images/req  │
│ Image (URL)     │ JPEG, PNG, GIF, WebP             │ 5MB per image, 20 images/req  │
│ PDF (as image)  │ Render pages as images first     │ Use azure-doc-intelligence     │
│                 │                                  │ for large PDFs                 │
└─────────────────┴──────────────────────────────────┴───────────────────────────────┘

Key limits:
  Max image file size:       5 MB
  Max images per request:    20
  Recommended max dimension: 1568px on the longest side
  Minimum useful dimension:  200px (smaller images lose detail)
  
Media type strings:
  JPEG: "image/jpeg"  (also for .jpg files)
  PNG:  "image/png"
  GIF:  "image/gif"
  WebP: "image/webp"
```

---

## 2. Image Token Costs and Optimization

### How Image Tokens Are Calculated

```
Claude resizes images before processing based on the longest dimension.
Token cost is based on the FINAL (processed) dimensions, not input dimensions.

Resize rules:
  If longest side > 1568px: resize to 1568px on longest side
  If longest side ≤ 1568px: use original dimensions
  
Token formula (after resize):
  tokens ≈ (width × height) / 750

Examples:
  1568×1568 (max square): 1568×1568/750 ≈ 3,278 tokens → ~$0.010 (Sonnet)
  1568×1024 (landscape):  1568×1024/750 ≈ 2,139 tokens → ~$0.006
  1024×768  (photo):      1024×768/750  ≈ 1,049 tokens → ~$0.003
  512×512   (thumbnail):  512×512/750   ≈   350 tokens → ~$0.001
  200×200   (icon):       200×200/750   ≈    53 tokens → ~$0.000016

Comparison:
  Processing 100 images:
    At 1568px (no resize): ~200K tokens → ~$0.60 (Sonnet)
    At 800px (resized):    ~85K tokens  → ~$0.26 (Sonnet)
    At 512px (thumbnail):  ~35K tokens  → ~$0.11 (Sonnet)
```

### Image Optimization Function

```python
from pathlib import Path
import io
import base64
from typing import Optional

def optimise_image_for_vision(
    image_source: str | bytes,
    max_dimension: int = 1024,
    quality: int = 85,
    output_format: str = "JPEG",
) -> tuple[bytes, str]:
    """
    Resize and compress an image for optimal Claude vision processing.
    
    Reduces token cost while preserving readability for text and detail recognition.
    
    Args:
        image_source:  File path (str) or raw bytes
        max_dimension: Max pixels on longest side (default: 1024)
                       Use 1568 for maximum quality
                       Use 800  for balance of quality/cost
                       Use 512  for thumbnails and simple classification
        quality:       JPEG quality 1-100 (default: 85)
        output_format: "JPEG" or "PNG" (default: "JPEG" — smaller files)
    
    Returns:
        (image_bytes, media_type) tuple
    
    Token cost impact:
        max_dimension=1568: ~2,500 tokens per image
        max_dimension=1024: ~1,400 tokens per image (44% reduction)
        max_dimension=512:  ~350  tokens per image  (86% reduction)
    """
    from PIL import Image  # pip install Pillow
    
    if isinstance(image_source, str):
        img = Image.open(image_source)
    else:
        img = Image.open(io.BytesIO(image_source))
    
    # Convert RGBA → RGB if saving as JPEG (JPEG doesn't support alpha)
    if output_format == "JPEG" and img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
        img = background
    
    # Resize to max_dimension on longest side
    img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)
    
    # Compress to bytes
    buffer = io.BytesIO()
    save_kwargs = {"format": output_format}
    if output_format == "JPEG":
        save_kwargs["quality"] = quality
        save_kwargs["optimize"] = True
    img.save(buffer, **save_kwargs)
    
    media_type = "image/jpeg" if output_format == "JPEG" else "image/png"
    return buffer.getvalue(), media_type

def load_image_as_base64(
    image_path: str,
    max_dimension: int = 1024,
) -> tuple[str, str]:
    """
    Load an image file and return (base64_string, media_type).
    
    Args:
        image_path:    Path to image file
        max_dimension: Resize to this dimension (default: 1024)
    
    Returns:
        (base64_encoded_string, media_type) ready for Claude API
    
    Usage:
        b64, mime = load_image_as_base64("dish_photo.jpg")
        # Use in API call: {"type": "base64", "media_type": mime, "data": b64}
    """
    image_bytes, media_type = optimise_image_for_vision(image_path, max_dimension)
    return base64.standard_b64encode(image_bytes).decode("utf-8"), media_type
```

---

## 3. Basic Image Analysis (Base64)

```python
import anthropic
import base64
import json
from pathlib import Path
import os

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

def analyse_dish_photo(image_path: str) -> dict:
    """
    Analyse a restaurant dish photo for quality assessment.
    
    Returns structured assessment of plating, ingredients, and presentation.
    
    Args:
        image_path: Path to dish photo (JPEG or PNG)
    
    Returns:
        {
            "plating_score":        int (1-10),
            "identified_components": list[str],
            "presentation_issues":  list[str],
            "temperature_visible":  bool,
            "garnish_quality":      str,
            "ready_for_service":    bool,
            "comments":             str,
        }
    
    Usage:
        result = analyse_dish_photo("photos/wagyu_beef_202601.jpg")
        if not result["ready_for_service"]:
            alert_kitchen(result["presentation_issues"])
    """
    # Load and optimise image
    image_data, media_type = load_image_as_base64(image_path, max_dimension=1024)
    
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": """Analyse this restaurant dish photo as a professional Michelin-starred chef.
                        
Return ONLY valid JSON (no explanation, no markdown fences):
{
  "plating_score": 1-10,
  "identified_components": ["list each visible ingredient or component"],
  "presentation_issues": ["list any issues, or empty array if none"],
  "temperature_visible": true or false,
  "garnish_quality": "excellent|good|adequate|poor",
  "portion_size": "large|appropriate|small",
  "ready_for_service": true or false,
  "comments": "one sentence professional assessment"
}"""
                    },
                ],
            }
        ],
    )
    
    text = response.content[0].text
    
    # Parse JSON response (handle possible fences)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Strip markdown fences if present
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse vision response: {text[:200]}")
```

---

## 4. URL-Based Image Input

```python
def analyse_wine_label_from_url(image_url: str) -> dict:
    """
    Extract wine details from a publicly accessible label photo.
    
    Use URL-based images when:
    - Image is already publicly hosted (CDN, Azure Blob with public access)
    - You want to avoid base64 encoding overhead
    - Image size is within 5MB limit
    
    Do NOT use URL-based images when:
    - Image requires authentication (use base64 instead)
    - Image is behind a firewall
    - URL may not be accessible at request time
    
    Args:
        image_url: Public HTTPS URL to wine label image
    
    Returns:
        {
            "producer":        str | null,
            "wine_name":       str | null,
            "vintage":         int | null,
            "appellation":     str | null,
            "grape_varieties": list[str],
            "alcohol_pct":     float | null,
            "region":          str | null,
            "classification":  str | null,
            "confidence":      float (0-1)
        }
    """
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "url",
                            "url": image_url,  # Must be HTTPS and publicly accessible
                        },
                    },
                    {
                        "type": "text",
                        "text": """Extract wine information from this label. Return ONLY valid JSON:
{
  "producer": "string or null if not visible",
  "wine_name": "string or null",
  "vintage": integer or null,
  "appellation": "string or null",
  "grape_varieties": ["array of grape variety strings, or empty"],
  "alcohol_pct": number or null,
  "region": "string or null",
  "classification": "e.g. Grand Cru, Premier Cru, or null",
  "confidence": 0.0-1.0
}
Use null for any field not clearly visible on the label."""
                    },
                ],
            }
        ],
    )
    
    try:
        return json.loads(response.content[0].text)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{.*\}', response.content[0].text, re.DOTALL)
        return json.loads(match.group()) if match else {}
```

---

## 5. Multi-Image Analysis and Comparison

```python
def compare_plating_versions(
    before_path: str,
    after_path: str,
    dish_name: str = "the dish",
) -> dict:
    """
    Compare two plating versions to identify improvements.
    
    Useful for:
    - Chef training: before/after comparison
    - Quality control: today's service vs standard
    - Menu development: A/B testing plating styles
    
    Args:
        before_path: Path to original/current plating photo
        after_path:  Path to revised/new plating photo
        dish_name:   Name of the dish for context
    
    Returns:
        {
            "overall_winner": "image_1" | "image_2" | "tie",
            "image_1_strengths": list[str],
            "image_2_strengths": list[str],
            "key_improvements": list[str],
            "recommendation": str
        }
    """
    def load_img(path: str) -> dict:
        b64, mime = load_image_as_base64(path, max_dimension=1024)
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": mime, "data": b64}
        }
    
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[
            {
                "role": "user",
                "content": [
                    load_img(before_path),
                    {"type": "text", "text": "Image 1 (Original plating)"},
                    load_img(after_path),
                    {"type": "text", "text": f"""Image 2 (Revised plating)

Compare these two platings of {dish_name} as a Michelin-trained chef.
Return ONLY valid JSON:
{{
  "overall_winner": "image_1 or image_2 or tie",
  "image_1_strengths": ["list"],
  "image_2_strengths": ["list"],
  "key_improvements_in_image_2": ["list of what improved"],
  "key_regressions_in_image_2": ["list of what got worse, or empty"],
  "recommendation": "one sentence professional recommendation"
}}"""},
                ],
            }
        ],
    )
    
    try:
        return json.loads(response.content[0].text)
    except json.JSONDecodeError:
        return {"recommendation": response.content[0].text[:300]}


def analyse_multiple_dishes(image_paths: list[str], max_batch: int = 5) -> list[dict]:
    """
    Analyse multiple dish photos in a single request (up to 20 images).
    
    More efficient than individual calls when processing a meal service.
    
    Args:
        image_paths: List of paths to dish photos
        max_batch:   Images per request batch (default: 5, max: 20)
    
    Returns:
        List of analysis dicts, one per image
    """
    all_results = []
    
    for batch_start in range(0, len(image_paths), max_batch):
        batch = image_paths[batch_start:batch_start + max_batch]
        
        content = []
        for i, path in enumerate(batch):
            b64, mime = load_image_as_base64(path, max_dimension=800)  # Smaller for batch
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": mime, "data": b64}
            })
            content.append({
                "type": "text",
                "text": f"Dish {batch_start + i + 1}: {Path(path).stem}"
            })
        
        content.append({
            "type": "text",
            "text": f"""Analyse each of the {len(batch)} dishes shown above.
Return a JSON array with one object per dish (in order):
[
  {{
    "dish_number": 1,
    "plating_score": 1-10,
    "ready_for_service": true or false,
    "critical_issues": ["list or empty"]
  }}
]"""
        })
        
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            messages=[{"role": "user", "content": content}]
        )
        
        try:
            batch_results = json.loads(response.content[0].text)
            all_results.extend(batch_results)
        except json.JSONDecodeError:
            # Fallback: return partial results
            all_results.extend([{"dish_number": batch_start + i + 1, "error": "parse_failed"} for i in range(len(batch))])
    
    return all_results
```

---

## 6. Document OCR via Vision

```python
def transcribe_handwritten_specials(image_path: str) -> list[dict]:
    """
    Transcribe a handwritten specials board or menu card.
    
    Use this instead of Azure Document Intelligence for:
    - Handwritten content
    - Stylized/creative typography  
    - Non-standard layouts
    - Diagrams or illustrations with text
    
    Args:
        image_path: Path to photo of specials board
    
    Returns:
        List of dish dicts:
        [{"dish_name": str, "description": str, "price_gbp": float|None, "dietary_flags": list[str]}]
    
    Usage:
        specials = transcribe_handwritten_specials("tonight_specials.jpg")
        for dish in specials:
            update_pos_system(dish)
    """
    b64, mime = load_image_as_base64(image_path, max_dimension=1568)  # Max quality for text
    
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": mime, "data": b64}
                    },
                    {
                        "type": "text",
                        "text": """Transcribe this specials board completely and accurately.

Return ONLY a JSON array (no explanation):
[
  {
    "dish_name": "exact name as written",
    "description": "full description as written",
    "price_gbp": null or number (e.g. 28.50),
    "dietary_flags": ["v" for vegetarian, "vg" for vegan, "gf" for gluten-free, "n" for contains nuts, etc.]
  }
]

Important:
- Preserve exact spelling and capitalisation from the board
- If price is not shown, use null
- If unsure about a character, use your best judgment"""
                    },
                ],
            }
        ],
    )
    
    try:
        return json.loads(response.content[0].text)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\[.*\]', response.content[0].text, re.DOTALL)
        return json.loads(match.group()) if match else []


def extract_receipt_data(receipt_image: str | bytes) -> dict:
    """
    Extract structured data from a receipt or invoice photo.
    
    Handles: printed receipts, handwritten receipts, photos of paper invoices.
    For digital PDFs use Azure Document Intelligence (faster + more accurate).
    
    Args:
        receipt_image: File path or bytes of receipt image
    
    Returns:
        {
            "vendor_name": str,
            "date": "YYYY-MM-DD" or null,
            "total": float or null,
            "currency": "GBP" etc.,
            "subtotal": float or null,
            "tax": float or null,
            "line_items": [{"description": str, "qty": float, "unit_price": float, "total": float}]
        }
    """
    if isinstance(receipt_image, str):
        b64, mime = load_image_as_base64(receipt_image, max_dimension=1568)
    else:
        b64 = base64.standard_b64encode(receipt_image).decode()
        mime = "image/jpeg"
    
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
                    {
                        "type": "text",
                        "text": """Extract receipt data. Return ONLY valid JSON:
{
  "vendor_name": "string or null",
  "date": "YYYY-MM-DD or null",
  "total": number or null,
  "currency": "GBP/USD/EUR etc.",
  "subtotal": number or null,
  "tax_amount": number or null,
  "tax_rate_pct": number or null,
  "line_items": [
    {"description": "string", "quantity": number, "unit_price": number, "total": number}
  ]
}
Use null for any fields not clearly visible."""
                    }
                ],
            }
        ],
    )
    
    try:
        return json.loads(response.content[0].text)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{.*\}', response.content[0].text, re.DOTALL)
        return json.loads(match.group()) if match else {}
```

---

## 7. Structured Output from Images

### Combining Vision with Pydantic Validation

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List

class WineLabelExtraction(BaseModel):
    """Validated wine label extraction result."""
    producer: Optional[str] = Field(None, description="Winery or producer name")
    wine_name: Optional[str] = Field(None, description="Wine cuvée or brand name")
    vintage: Optional[int] = Field(None, ge=1800, le=2030, description="Vintage year")
    appellation: Optional[str] = Field(None, description="AOC/DOC/AVA designation")
    grape_varieties: List[str] = Field(default_factory=list)
    alcohol_pct: Optional[float] = Field(None, ge=0, le=25, description="Alcohol percentage")
    region: Optional[str] = Field(None, description="Wine region")
    classification: Optional[str] = Field(None, description="Quality classification")
    confidence: float = Field(0.0, ge=0, le=1, description="Extraction confidence")
    
    @validator("vintage")
    def vintage_in_range(cls, v):
        if v is not None and not (1850 <= v <= 2030):
            raise ValueError(f"Vintage {v} is outside expected range 1850-2030")
        return v

def extract_wine_label_validated(image_path: str) -> WineLabelExtraction:
    """
    Extract wine label info with Pydantic validation.
    
    Returns:
        WineLabelExtraction model (validated + type-safe)
    
    Usage:
        wine = extract_wine_label_validated("cellar/bordeaux_2018.jpg")
        print(f"{wine.producer} {wine.vintage}")  # "Château Margaux 2018"
        wine.dict()  # → Full dict for database storage
    """
    raw = analyse_wine_label_from_url(f"file://{Path(image_path).absolute()}")
    # Note: For production use base64 loading instead of file:// URL
    
    try:
        return WineLabelExtraction(**raw)
    except Exception as e:
        # Return partial model on validation failure
        valid_fields = {
            k: v for k, v in raw.items()
            if k in WineLabelExtraction.__fields__
        }
        return WineLabelExtraction(**valid_fields)
```

---

## 8. Vision vs Azure Document Intelligence

```
Decision Matrix: When to use Claude Vision vs Document Intelligence
────────────────────────────────────────────────────────────────────

USE CLAUDE VISION WHEN:
  ✅ Handwritten content (notes, specials boards, ledger entries)
  ✅ Highly visual content (photos, diagrams, charts, infographics)
  ✅ Creative/artistic typography that breaks standard OCR
  ✅ Wine labels (non-standard layout, multiple languages)
  ✅ Food photos for quality assessment
  ✅ Non-standard document layouts
  ✅ Need semantic understanding of visual content ("describe the mood")
  ✅ Multi-image comparison tasks

USE AZURE DOCUMENT INTELLIGENCE WHEN:
  ✅ Standard form types (invoices, receipts, ID cards, tax forms)
  ✅ Multi-page PDFs with consistent structure
  ✅ Need confidence scores per extracted field
  ✅ Need bounding box coordinates for each field
  ✅ High-volume structured extraction (> 1,000/day) — DI is cheaper
  ✅ Pre-built models: invoices, receipts, business cards, IDs
  ✅ Tables and forms with clearly defined fields

COST COMPARISON (approximate 2026):
  Claude Vision (Sonnet): $0.003-0.009 per image + $0.003/1K output tokens
  Document Intelligence:  $0.001-0.003 per page (prebuilt models)
  → DI is 2-3× cheaper for standard documents at volume
```

```python
def smart_extraction_router(
    image_path: str,
    document_type: str = "auto",
) -> dict:
    """
    Route to the best extraction method based on document type.
    
    Args:
        image_path:    Path to image or document
        document_type: "auto" | "invoice" | "receipt" | "handwritten" | 
                       "wine_label" | "dish_photo" | "form" | "chart"
    
    Returns:
        Extracted data dict
    """
    # Auto-detect document type from filename + extension
    if document_type == "auto":
        name = Path(image_path).stem.lower()
        if any(w in name for w in ["invoice", "inv_", "bill"]):
            document_type = "invoice"
        elif any(w in name for w in ["receipt", "rcpt"]):
            document_type = "receipt"
        elif any(w in name for w in ["wine", "label", "bottle"]):
            document_type = "wine_label"
        elif any(w in name for w in ["dish", "food", "plate", "course"]):
            document_type = "dish_photo"
        elif any(w in name for w in ["specials", "handwritten", "board"]):
            document_type = "handwritten"
        else:
            document_type = "unknown"
    
    # Route to appropriate extractor
    ROUTE_MAP = {
        # Document Intelligence for standard structured documents
        "invoice":     _extract_with_document_intelligence,
        "receipt":     _extract_with_document_intelligence,
        "form":        _extract_with_document_intelligence,
        
        # Claude Vision for visual/creative content
        "wine_label":  analyse_wine_label_from_url,
        "dish_photo":  analyse_dish_photo,
        "handwritten": transcribe_handwritten_specials,
        "chart":       _extract_chart_data_with_vision,
        
        # Default to Claude Vision for unknowns
        "unknown":     _generic_vision_extraction,
    }
    
    extractor = ROUTE_MAP.get(document_type, _generic_vision_extraction)
    return extractor(image_path)


def _extract_with_document_intelligence(document_path: str) -> dict:
    """
    Use Azure Document Intelligence for standard document types.
    Requires: pip install azure-ai-formrecognizer
    """
    from azure.ai.formrecognizer import DocumentAnalysisClient
    from azure.core.credentials import AzureKeyCredential
    
    endpoint = os.environ["AZURE_FORM_RECOGNIZER_ENDPOINT"]
    key      = os.environ["AZURE_FORM_RECOGNIZER_KEY"]
    
    client = DocumentAnalysisClient(endpoint, AzureKeyCredential(key))
    
    with open(document_path, "rb") as f:
        poller = client.begin_analyze_document("prebuilt-invoice", document=f)
    
    result = poller.result()
    
    # Extract key invoice fields
    if result.documents:
        doc = result.documents[0]
        fields = doc.fields
        return {
            "vendor_name": fields.get("VendorName", {}).value if fields.get("VendorName") else None,
            "invoice_date": str(fields.get("InvoiceDate", {}).value) if fields.get("InvoiceDate") else None,
            "total_amount": fields.get("InvoiceTotal", {}).value.amount if fields.get("InvoiceTotal") else None,
            "currency": fields.get("InvoiceTotal", {}).value.symbol if fields.get("InvoiceTotal") else "GBP",
            "confidence": doc.confidence,
        }
    return {}
```

---

## 9. Batch Image Processing

```python
import asyncio
from typing import AsyncGenerator

async def process_images_async(
    image_paths: list[str],
    processor_fn: callable,
    max_concurrent: int = 5,
) -> list[dict]:
    """
    Process multiple images concurrently with rate limiting.
    
    Args:
        image_paths:    List of paths to process
        processor_fn:   Async function that takes image_path → dict
        max_concurrent: Max parallel requests (default: 5)
    
    Returns:
        List of results in original order
    
    Usage:
        results = await process_images_async(
            dish_photos,
            processor_fn=lambda p: analyse_dish_photo_async(p),
            max_concurrent=5,
        )
    
    Performance:
        Sequential:  20 images × 3s each = 60s
        Parallel:    20 images, 5 at a time = ~12s (5× speedup)
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_one(path: str, index: int) -> tuple[int, dict]:
        async with semaphore:
            result = await asyncio.get_event_loop().run_in_executor(
                None, processor_fn, path
            )
            return index, result
    
    tasks = [process_one(path, i) for i, path in enumerate(image_paths)]
    results_with_indices = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Sort by original index and handle errors
    ordered = sorted(
        [(i, r) for i, r in results_with_indices if not isinstance(r, Exception)],
        key=lambda x: x[0]
    )
    
    return [r for _, r in ordered]


def batch_label_scan(wine_label_paths: list[str]) -> list[dict]:
    """
    Scan a batch of wine label photos for cellar inventory.
    
    Processes up to 5 labels in each API call to reduce overhead.
    
    Args:
        wine_label_paths: List of paths to wine label photos
    
    Returns:
        List of extracted wine data dicts
    """
    BATCH_SIZE = 5
    all_results = []
    
    for i in range(0, len(wine_label_paths), BATCH_SIZE):
        batch = wine_label_paths[i:i + BATCH_SIZE]
        
        content = []
        for j, path in enumerate(batch):
            b64, mime = load_image_as_base64(path, max_dimension=800)
            content.append({"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}})
            content.append({"type": "text", "text": f"Label {j + 1}:"})
        
        content.append({
            "type": "text",
            "text": f"""Extract wine information from each of the {len(batch)} labels.
Return a JSON array with one object per label (in order):
[
  {{"label_number": 1, "producer": "string or null", "wine_name": "string or null",
    "vintage": integer or null, "appellation": "string or null", "confidence": 0.0-1.0}},
  ...
]"""
        })
        
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            messages=[{"role": "user", "content": content}]
        )
        
        try:
            batch_results = json.loads(response.content[0].text)
            all_results.extend(batch_results)
        except json.JSONDecodeError:
            all_results.extend([{"label_number": i + j + 1, "error": "parse_failed"} for j in range(len(batch))])
    
    return all_results
```

---

## 10. Vision with Tool Use

```python
def analyse_and_lookup_wine(image_path: str) -> dict:
    """
    Identify a wine from its label, then look it up in the cellar inventory.
    
    Combines vision (label identification) with tool use (inventory lookup).
    """
    
    tools = [
        {
            "name": "search_wine_inventory",
            "description": "Search the restaurant's wine inventory by producer and vintage.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "producer":   {"type": "string", "description": "Winery/producer name"},
                    "vintage":    {"type": "integer", "description": "Year of vintage"},
                    "wine_name":  {"type": "string", "description": "Wine name/cuvée"},
                },
                "required": ["producer"],
            }
        }
    ]
    
    b64, mime = load_image_as_base64(image_path, max_dimension=1024)
    
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
                {"type": "text", "text": "Identify this wine label, then search our inventory to see how many bottles we have."}
            ]
        }
    ]
    
    # Agentic loop
    for _ in range(5):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            tools=tools,
            messages=messages,
        )
        
        if response.stop_reason == "end_turn":
            return {"analysis": response.content[0].text}
        
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    if block.name == "search_wine_inventory":
                        result = search_wine_inventory_db(**block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result)
                        })
            
            messages.append({"role": "user", "content": tool_results})
    
    return {"error": "Agent loop did not complete"}
```

---

## 11. Junior Walkthrough — Analyse Your First Image

**Scenario**: "I want to analyse a photo of a dish. How do I start?"

**Step 1: Load the image as base64**

```python
import anthropic, base64
from pathlib import Path

client = anthropic.Anthropic()

# Load your image
image_path = "photo.jpg"
image_bytes = Path(image_path).read_bytes()
image_data = base64.standard_b64encode(image_bytes).decode("utf-8")
```

**Step 2: Send to Claude with the image content block**

```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=500,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",  # Match your file type
                        "data": image_data,
                    },
                },
                {
                    "type": "text",
                    "text": "Describe this dish in detail.",
                },
            ],
        }
    ],
)

print(response.content[0].text)
```

**Step 3: Add the optimiser function for cost savings**

```python
# Instead of raw bytes, use the optimiser to resize first
b64, mime = load_image_as_base64("photo.jpg", max_dimension=1024)
# This reduces tokens by ~40% vs full-size images
```

**Step 4: Request structured JSON output**

```python
# Replace the text question with a structured request
"text": """Analyse this dish. Return ONLY valid JSON:
{"name": "dish name", "score": 1-10, "issues": ["list or empty"]}"""
```

---

## 12. Senior Patterns — Production Vision Pipeline

```python
class VisionPipeline:
    """
    Production vision pipeline with routing, caching, and telemetry.
    
    Features:
    - Smart routing between Claude Vision and Document Intelligence
    - Image optimization before API calls
    - Response caching for identical images
    - Full Application Insights telemetry
    - Pydantic validation on all outputs
    """
    
    def __init__(self, config: dict):
        self.cache = {}  # Use Redis in production
        self.doc_client = self._init_doc_client(config)
    
    def process(self, image_path: str, task: str) -> dict:
        """
        Process an image through the optimal pipeline.
        
        Args:
            image_path: Path to image file
            task:       "quality_check" | "label_scan" | "receipt" | "specials_board"
        
        Returns:
            Extracted/analysed data dict
        """
        import hashlib
        
        # Cache key based on image hash + task
        img_hash = hashlib.md5(Path(image_path).read_bytes()).hexdigest()
        cache_key = f"{img_hash}:{task}"
        
        if cache_key in self.cache:
            return {**self.cache[cache_key], "from_cache": True}
        
        # Route to correct processor
        processors = {
            "quality_check":   self._quality_check,
            "label_scan":      self._label_scan,
            "receipt":         self._receipt_extraction,
            "specials_board":  self._specials_transcription,
        }
        
        processor = processors.get(task, self._generic_vision)
        result = processor(image_path)
        
        # Cache result (for 1 hour)
        self.cache[cache_key] = result
        return result
    
    def _quality_check(self, path: str) -> dict:
        return analyse_dish_photo(path)
    
    def _label_scan(self, path: str) -> dict:
        wine = extract_wine_label_validated(path)
        return wine.dict()
    
    def _receipt_extraction(self, path: str) -> dict:
        # Route to Document Intelligence for receipts
        return _extract_with_document_intelligence(path)
    
    def _specials_transcription(self, path: str) -> dict:
        dishes = transcribe_handwritten_specials(path)
        return {"dishes": dishes, "count": len(dishes)}
    
    def _generic_vision(self, path: str) -> dict:
        b64, mime = load_image_as_base64(path)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
                {"type": "text", "text": "Describe the contents of this image in detail."}
            ]}]
        )
        return {"description": response.content[0].text}
    
    def _init_doc_client(self, config: dict):
        try:
            from azure.ai.formrecognizer import DocumentAnalysisClient
            from azure.core.credentials import AzureKeyCredential
            return DocumentAnalysisClient(
                config["doc_intelligence_endpoint"],
                AzureKeyCredential(config["doc_intelligence_key"]),
            )
        except Exception:
            return None
```

---

## 13. Tips, Tricks, and Gotchas

### Tips

1. **Always optimise images before sending** — resizing to 1024px saves 40–60% on image tokens with minimal quality loss for most tasks
2. **Use JPEG not PNG for photos** — JPEG files are 5–10× smaller than PNG for photographic content; same base64 size benefit
3. **1568px for text-heavy images** — for wine labels, specials boards, or menus with small text, use max_dimension=1568 to preserve readability
4. **Batch images in a single call** — up to 20 images per request; 5 images per call is a good batch size for structured extraction

### Tricks

5. **Prefill JSON with `{`** — add `{"role": "assistant", "content": "{"}` to force JSON start even for vision tasks
6. **Include label context in the prompt** — "this is a wine label from France" helps when the label is partially obscured
7. **For low-confidence results, retry with higher resolution** — if confidence < 0.7, reload with max_dimension=1568 and retry
8. **Use URL input for public images in production** — avoids base64 encoding overhead; URL images are fetched server-side

### Gotchas

9. **RGBA to RGB conversion required for JPEG** — if you save an RGBA PNG as JPEG without conversion, Pillow will error. Always convert first.
10. **5MB limit per image is on the original bytes, not base64** — base64 adds ~33% overhead. A 5MB image becomes ~6.7MB in base64 — still within the content limit but be aware of request size.
11. **URL images must be publicly accessible** — private S3/Blob URLs with SAS tokens sometimes work but aren't guaranteed. Use base64 for reliability.
12. **Vision quality degrades below 200px** — images smaller than 200×200 may not contain enough detail for accurate text extraction
13. **Don't use vision for password-protected PDFs** — they can't be rendered to images without decryption first

---

## 14. Quick Reference Cheatsheet

```python
# ═══════════════════════════════════════════════════════════════
# MULTIMODAL / VISION QUICK REFERENCE
# ═══════════════════════════════════════════════════════════════

# 1. LOAD IMAGE AS BASE64
b64_str, mime_type = load_image_as_base64("photo.jpg", max_dimension=1024)

# 2. IMAGE CONTENT BLOCK (base64)
image_block = {
    "type": "image",
    "source": {
        "type": "base64",
        "media_type": "image/jpeg",  # or image/png, image/webp, image/gif
        "data": b64_str,
    }
}

# 3. IMAGE CONTENT BLOCK (URL)
image_block = {
    "type": "image",
    "source": {
        "type": "url",
        "url": "https://example.com/image.jpg",  # Must be HTTPS
    }
}

# 4. MULTI-CONTENT MESSAGE
messages = [{
    "role": "user",
    "content": [
        image_block,
        {"type": "text", "text": "Analyse this image."}
    ]
}]

# 5. TOKEN COST ESTIMATE
# tokens ≈ (width × height) / 750
# 1024×1024 → ~1,400 tokens → ~$0.004 (Sonnet input)
# 512×512   → ~350 tokens   → ~$0.001 (Sonnet input)

# 6. OPTIMAL DIMENSIONS
# max_dimension=1568: Labels, text-heavy, small print
# max_dimension=1024: Dishes, food photos, standard analysis
# max_dimension=800:  Batch processing, simple classification
# max_dimension=512:  Thumbnails, quick categorisation

# 7. MEDIA TYPE MAP
EXT_TO_MIME = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

# 8. LIMITS
# Max images per request:  20
# Max image size:          5 MB (original, pre-base64)
# Min useful dimension:    200px

# 9. ROUTING DECISION
# Claude Vision:              handwriting, labels, dishes, diagrams
# Document Intelligence:      invoices, receipts, standard forms, multi-page PDFs

# 10. FORCE JSON OUTPUT
# Add as last content block:
{"type": "text", "text": "Return ONLY valid JSON: {...schema...}"}
# Or use assistant prefill: {"role": "assistant", "content": "{"}
```
