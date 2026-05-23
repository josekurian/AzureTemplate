# rag-patterns.md — Retrieval-Augmented Generation with Claude

> **Purpose**: Complete guide to building accurate, grounded, citation-aware RAG systems with Claude — from indexing to retrieval, grounding, and quality evaluation.  
> **Owner**: jose@hybridgenai.com  
> **Updated**: 2026-05-22

---

## Navigation

1. [Why RAG Over Pure Generation](#1-why-rag-over-pure-generation)
2. [RAG Pipeline Architecture](#2-rag-pipeline-architecture)
3. [Document Ingestion and Chunking](#3-document-ingestion-and-chunking)
4. [Embedding and Indexing](#4-embedding-and-indexing)
5. [Query Analysis and Rewriting](#5-query-analysis-and-rewriting)
6. [Hybrid Search Configuration](#6-hybrid-search-configuration)
7. [Context Window Construction](#7-context-window-construction)
8. [RAG System Prompt Design](#8-rag-system-prompt-design)
9. [Groundedness Evaluation](#9-groundedness-evaluation)
10. [Advanced RAG Patterns](#10-advanced-rag-patterns)
11. [Junior Quick-Start Walkthrough](#11-junior-quick-start-walkthrough)
12. [Senior Patterns and Production Hardening](#12-senior-patterns-and-production-hardening)
13. [Tips, Tricks and Gotchas](#13-tips-tricks-and-gotchas)
14. [Quick Reference Cheatsheet](#14-quick-reference-cheatsheet)

---

## 1. Why RAG Over Pure Generation

| Approach | Hallucination Risk | Data Freshness | Customisation | Cost | Use When |
|---|---|---|---|---|---|
| Pure generation | High | Training cutoff (May 2025) | Low (prompt only) | Low | General knowledge only |
| Fine-tuning | Medium | Static after training | High (behaviour) | Very High | Style/behaviour at scale |
| RAG | Low | Real-time (update anytime) | High (any content) | Medium | Domain knowledge, facts, documents |
| RAG + Fine-tuning | Lowest | Real-time | Highest | Highest | Only for extreme quality requirements |

**RAG is the right choice when:**
- Your data changes (menus, prices, policies, inventory)
- You need citations/provenance ("Source: policy_v3.pdf, page 4")
- Hallucination is a safety risk (allergen info, legal, medical)
- Your domain is not well-covered by Claude's training data

---

## 2. RAG Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     INDEXING PIPELINE (run once / on update)        │
│                                                                      │
│  Documents (PDF, DOCX, TXT)                                          │
│       ↓                                                              │
│  [1] Document Ingestion → Extract text, tables, metadata            │
│       ↓                                                              │
│  [2] Chunking → Split into 300-600 token chunks with overlap        │
│       ↓                                                              │
│  [3] Embedding → text-embedding-3-large → 3072-dim vectors          │
│       ↓                                                              │
│  [4] Index Upload → Azure AI Search (vector + keyword fields)       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                     QUERY PIPELINE (run per request)                │
│                                                                      │
│  User Query                                                          │
│       ↓                                                              │
│  [5] Query Analysis → Rewrite/expand/decompose the query            │
│       ↓                                                              │
│  [6] Retrieval → Hybrid search: BM25 + vector + semantic ranker     │
│                   top_k = 5-8 chunks                                 │
│       ↓                                                              │
│  [7] Context Building → Format chunks with source metadata          │
│       ↓                                                              │
│  [8] Generation → Claude with grounded context in <context> tags    │
│       ↓                                                              │
│  [9] Citation Extraction → Parse [Source: X] references             │
│       ↓                                                              │
│  [10] Groundedness Check → Score response against context           │
│       ↓                                                              │
│  Response delivered to user                                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Document Ingestion and Chunking

### Chunking Strategy by Document Type

Different content requires different chunking — one-size-fits-all chunking is the most common RAG mistake.

```python
from typing import Optional
import re

# Recommended chunk sizes by document type
CHUNK_CONFIG = {
    "wine_list":        {"size": 150, "overlap": 20,  "strategy": "entry"},    # One wine per chunk
    "food_menu":        {"size": 250, "overlap": 30,  "strategy": "section"},  # One course section
    "policy_document":  {"size": 500, "overlap": 50,  "strategy": "paragraph"},
    "faq":              {"size": 300, "overlap": 0,   "strategy": "qa_pair"},  # Each Q+A as one chunk
    "handbook":         {"size": 600, "overlap": 100, "strategy": "section"},
    "general_text":     {"size": 500, "overlap": 50,  "strategy": "sliding"},
}

# Strategy 1: Fixed sliding window (simple, predictable)
def chunk_sliding_window(
    text: str,
    chunk_size_tokens: int = 500,
    overlap_tokens: int = 50
) -> list[dict]:
    """
    Split text into overlapping chunks.
    Good for: general prose, policies, handbooks.

    Args:
        text: Input text to chunk
        chunk_size_tokens: Target tokens per chunk (~0.75 words/token)
        overlap_tokens: Overlap between adjacent chunks (prevents context loss)

    Returns:
        List of chunks with text and metadata
    """
    words = text.split()
    # Approximate: 1 token ≈ 0.75 words
    words_per_chunk = int(chunk_size_tokens * 0.75)
    overlap_words = int(overlap_tokens * 0.75)

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(words):
        end = min(start + words_per_chunk, len(words))
        chunk_text = " ".join(words[start:end])

        chunks.append({
            "chunk_index": chunk_index,
            "text": chunk_text,
            "word_count": end - start,
            "start_word": start,
            "end_word": end
        })

        chunk_index += 1
        start = end - overlap_words  # Backtrack by overlap

    return chunks

# Strategy 2: Sentence-boundary chunking (preserves semantic units)
def chunk_by_sentences(
    text: str,
    sentences_per_chunk: int = 5,
    overlap_sentences: int = 1
) -> list[dict]:
    """
    Split text at sentence boundaries.
    Good for: conversational content, descriptions, FAQs.
    """
    # Simple sentence splitter (use nltk or spacy in production)
    sentence_endings = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
    sentences = sentence_endings.split(text)

    chunks = []
    for i in range(0, len(sentences), sentences_per_chunk - overlap_sentences):
        chunk_sentences = sentences[i:i + sentences_per_chunk]
        if not chunk_sentences:
            break
        chunks.append({
            "chunk_index": i // (sentences_per_chunk - overlap_sentences),
            "text": " ".join(chunk_sentences),
            "sentence_count": len(chunk_sentences)
        })

    return chunks

# Strategy 3: Structural / section chunking (best for documents with headers)
def chunk_by_sections(
    text: str,
    min_section_tokens: int = 100,
    max_section_tokens: int = 600
) -> list[dict]:
    """
    Split text at markdown/heading boundaries.
    Good for: policy documents, menus, wikis, handbooks with clear sections.
    """
    # Split at headings (# Header or ALL CAPS lines)
    heading_pattern = re.compile(r'^(#{1,4}\s.+|[A-Z][A-Z\s:]{3,})\s*$', re.MULTILINE)

    parts = heading_pattern.split(text)
    sections = []
    current_heading = "Introduction"

    for i, part in enumerate(parts):
        if heading_pattern.match(part.strip()):
            current_heading = part.strip().lstrip('#').strip()
        elif part.strip():
            word_count = len(part.split())
            if word_count > 5:  # Skip tiny fragments
                sections.append({
                    "heading": current_heading,
                    "text": part.strip(),
                    "word_count": word_count
                })

    return sections

# Strategy 4: Wine list / menu item chunking (one item = one chunk)
def chunk_wine_list(wine_list_text: str) -> list[dict]:
    """
    Parse structured wine list into individual wine entries.
    Each wine becomes its own searchable chunk.
    """
    # Assume wine entries are separated by blank lines or numbered
    entries = re.split(r'\n\s*\n', wine_list_text.strip())
    chunks = []

    for i, entry in enumerate(entries):
        if entry.strip():
            chunks.append({
                "chunk_index": i,
                "text": entry.strip(),
                "document_type": "wine_list",
                "item_index": i
            })

    return chunks
```

---

### Document Metadata Enrichment

Each chunk should carry metadata for filtering, citation, and debugging.

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class DocumentChunk:
    """
    Enriched document chunk ready for indexing.
    All fields are searchable/filterable in Azure AI Search.
    """
    id: str                          # Unique chunk ID: "doc_name_chunk_001"
    document_name: str               # "wine_list_2026.pdf"
    document_type: str               # "wine_list" | "menu" | "policy" | "faq"
    chunk_index: int                 # Position within document
    heading: str                     # Section heading (if structural chunking)
    text: str                        # The actual content
    word_count: int
    page_number: Optional[int]       # PDF page (if available)
    last_updated: str                # ISO 8601 date
    tags: list[str]                  # ["wine", "red", "france"] for boosting
    content_vector: list[float]      # Will be filled by embedding step

def build_chunk_id(document_name: str, chunk_index: int) -> str:
    """Generate deterministic chunk ID for deduplication."""
    safe_name = re.sub(r'[^a-z0-9]', '_', document_name.lower())
    return f"{safe_name}_chunk_{chunk_index:04d}"
```

---

## 4. Embedding and Indexing

```python
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchField,
    SearchFieldDataType, VectorSearch, HnswAlgorithmConfiguration,
    VectorSearchProfile, SemanticConfiguration, SemanticField,
    SemanticPrioritizedFields, SemanticSearch
)
from azure.identity import DefaultAzureCredential

# Initialize clients
credential = DefaultAzureCredential()
openai_client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    credential=credential,
    api_version="2024-05-01-preview"
)

EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSIONS = 3072

def generate_embeddings_batch(
    texts: list[str],
    batch_size: int = 100
) -> list[list[float]]:
    """
    Generate embeddings for a list of texts in batches.
    Handles rate limits with retry logic.

    Args:
        texts: List of text strings to embed
        batch_size: API batch size (max ~2048 for text-embedding-3-large)

    Returns:
        List of embedding vectors (3072 floats each for text-embedding-3-large)
    """
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        # Rate limit: brief pause between batches
        if i > 0:
            time.sleep(0.5)

        response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch
        )
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)
        print(f"Embedded {i + len(batch)}/{len(texts)} chunks")

    return all_embeddings

def create_search_index(index_name: str, search_endpoint: str):
    """
    Create an Azure AI Search index with vector + keyword + semantic search.
    Run this ONCE when setting up the system.
    """
    index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)

    fields = [
        SimpleField("id", SearchFieldDataType.String, key=True),
        SearchableField("document_name", SearchFieldDataType.String, filterable=True),
        SearchableField("document_type", SearchFieldDataType.String, filterable=True),
        SearchableField("heading", SearchFieldDataType.String),
        SearchableField("text", SearchFieldDataType.String),
        SimpleField("chunk_index", SearchFieldDataType.Int32, filterable=True, sortable=True),
        SimpleField("page_number", SearchFieldDataType.Int32, filterable=True),
        SimpleField("last_updated", SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
        SimpleField("tags", SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True),
        # Vector field for semantic similarity
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBEDDING_DIMENSIONS,
            vector_search_profile_name="lumiere-vector-profile"
        )
    ]

    # HNSW vector search configuration
    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(
            name="lumiere-hnsw",
            parameters={
                "m": 4,              # Connections per node (higher = better recall, more memory)
                "efConstruction": 400,  # Index build quality (higher = slower build, better recall)
                "efSearch": 500,        # Query quality (higher = slower query, better recall)
                "metric": "cosine"   # "cosine" for text embeddings
            }
        )],
        profiles=[VectorSearchProfile(
            name="lumiere-vector-profile",
            algorithm_configuration_name="lumiere-hnsw"
        )]
    )

    # Semantic search configuration (enables neural re-ranking)
    semantic_config = SemanticConfiguration(
        name="lumiere-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            content_fields=[SemanticField(field_name="text")],
            title_field=SemanticField(field_name="heading"),
            keywords_fields=[SemanticField(field_name="tags")]
        )
    )

    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=SemanticSearch(configurations=[semantic_config])
    )

    index_client.create_or_update_index(index)
    print(f"Index '{index_name}' created/updated successfully")

def upload_chunks_to_index(
    chunks: list[DocumentChunk],
    search_endpoint: str,
    index_name: str,
    batch_size: int = 500
):
    """
    Upload enriched, embedded chunks to Azure AI Search.
    """
    search_client = SearchClient(
        endpoint=search_endpoint,
        index_name=index_name,
        credential=credential
    )

    # Convert dataclasses to dicts for upload
    documents = []
    for chunk in chunks:
        doc = {
            "id": chunk.id,
            "document_name": chunk.document_name,
            "document_type": chunk.document_type,
            "heading": chunk.heading or "",
            "text": chunk.text,
            "chunk_index": chunk.chunk_index,
            "page_number": chunk.page_number or 0,
            "last_updated": chunk.last_updated,
            "tags": chunk.tags,
            "content_vector": chunk.content_vector
        }
        documents.append(doc)

    # Upload in batches
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        result = search_client.upload_documents(batch)
        succeeded = sum(1 for r in result if r.succeeded)
        print(f"Batch {i//batch_size + 1}: {succeeded}/{len(batch)} uploaded")
```

---

## 5. Query Analysis and Rewriting

Direct user queries are often too short and ambiguous for optimal retrieval. Rewrite them first.

```python
QUERY_REWRITER_PROMPT = """
You are a search query specialist. Rewrite the user's question to improve document retrieval.

Rewriting rules:
1. Expand abbreviations ("veg" → "vegetarian")
2. Add synonyms for technical terms ("Burgundy" → "Burgundy Bourgogne Pinot Noir France")
3. Convert colloquial to formal ("go with" → "pair with food pairing")
4. If multi-part question, split into independent queries
5. Add document-type hint if obvious

Return ONLY valid JSON, no explanation:
{
  "primary_query": "expanded main query",
  "secondary_queries": ["alternative phrasing 1", "alternative phrasing 2"],
  "document_type_hint": "wine_list" | "menu" | "policy" | "faq" | null,
  "is_safety_query": true | false
}

User question: {question}
"""

def analyse_and_rewrite_query(
    question: str,
    model: str = "claude-haiku-4-5-20251001"  # Fast/cheap for preprocessing
) -> dict:
    """
    Analyse and rewrite a query for optimal retrieval.

    Returns:
        {
            "primary_query": str,
            "secondary_queries": list[str],
            "document_type_hint": str | None,
            "is_safety_query": bool  # True if allergen/medical query
        }

    Example:
        analyse_and_rewrite_query("any veg mains?")
        → {"primary_query": "vegetarian main course options menu",
           "secondary_queries": ["plant-based dishes", "meat-free options"],
           "document_type_hint": "menu",
           "is_safety_query": false}
    """
    response = client.messages.create(
        model=model,
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": QUERY_REWRITER_PROMPT.format(question=question)
        }]
    )

    try:
        return parse_claude_json(response.content[0].text)
    except Exception:
        # Fallback: use original query if parsing fails
        return {
            "primary_query": question,
            "secondary_queries": [],
            "document_type_hint": None,
            "is_safety_query": False
        }

def detect_query_intent(question: str) -> str:
    """
    Classify query intent for routing to appropriate search parameters.

    Returns: "wine_recommendation" | "allergen_check" | "reservation" |
             "menu_lookup" | "policy_lookup" | "general"
    """
    q_lower = question.lower()

    if any(w in q_lower for w in ["allerg", "intolerant", "dairy", "gluten", "nut", "shellfish"]):
        return "allergen_check"
    elif any(w in q_lower for w in ["wine", "bottle", "glass", "sommelier", "pair"]):
        return "wine_recommendation"
    elif any(w in q_lower for w in ["book", "reservation", "table", "available"]):
        return "reservation"
    elif any(w in q_lower for w in ["menu", "dish", "course", "dessert", "starter", "main"]):
        return "menu_lookup"
    elif any(w in q_lower for w in ["policy", "dress code", "deposit", "cancel", "hours"]):
        return "policy_lookup"
    else:
        return "general"
```

---

## 6. Hybrid Search Configuration

```python
from azure.search.documents import SearchClient
from azure.search.documents.models import (
    VectorizedQuery, QueryType, QueryLanguage
)

# Search parameters by query intent
SEARCH_CONFIG = {
    "allergen_check": {
        "top_k": 8,         # More results for safety-critical queries
        "use_semantic": True,
        "semantic_config": "lumiere-semantic-config",
        "score_threshold": 0.5,  # Lower threshold to catch edge cases
        "document_types": ["menu", "allergen_guide"]
    },
    "wine_recommendation": {
        "top_k": 6,
        "use_semantic": True,
        "semantic_config": "lumiere-semantic-config",
        "score_threshold": 0.7,
        "document_types": ["wine_list"]
    },
    "menu_lookup": {
        "top_k": 5,
        "use_semantic": True,
        "semantic_config": "lumiere-semantic-config",
        "score_threshold": 0.6,
        "document_types": ["menu"]
    },
    "policy_lookup": {
        "top_k": 3,
        "use_semantic": False,   # Keyword search better for exact policy terms
        "score_threshold": 0.5,
        "document_types": ["policy", "faq", "handbook"]
    },
    "general": {
        "top_k": 5,
        "use_semantic": True,
        "semantic_config": "lumiere-semantic-config",
        "score_threshold": 0.6,
        "document_types": None  # Search all document types
    }
}

def hybrid_semantic_search(
    query: str,
    query_embedding: list[float],
    intent: str = "general",
    search_endpoint: str = "",
    index_name: str = "lumiere-knowledge"
) -> list[dict]:
    """
    Full hybrid + semantic search combining BM25 + vector + neural re-ranker.

    The three-way combination:
    1. BM25 (keyword): exact term matches — good for product names, codes
    2. Vector (semantic): meaning matches — good for "pair with lamb" → red wine
    3. Semantic ranker: neural re-ranking of top results for best precision

    Args:
        query: The search query (rewritten or original)
        query_embedding: Pre-computed query embedding vector
        intent: Query intent for parameter selection
        search_endpoint: Azure AI Search endpoint URL
        index_name: Index to search

    Returns:
        List of ranked chunks with text, metadata, and scores
    """
    config = SEARCH_CONFIG.get(intent, SEARCH_CONFIG["general"])

    search_client = SearchClient(
        endpoint=search_endpoint,
        index_name=index_name,
        credential=DefaultAzureCredential()
    )

    vector_query = VectorizedQuery(
        vector=query_embedding,
        k_nearest_neighbors=config["top_k"] * 3,  # Over-retrieve; let ranker select best
        fields="content_vector"
    )

    # Build filter expression
    filter_expr = None
    if config.get("document_types"):
        type_filters = " or ".join(
            f"document_type eq '{dt}'" for dt in config["document_types"]
        )
        filter_expr = f"({type_filters})"

    # Execute hybrid search
    search_kwargs = {
        "search_text": query,
        "vector_queries": [vector_query],
        "filter": filter_expr,
        "top": config["top_k"],
        "select": ["id", "document_name", "document_type", "heading", "text",
                   "page_number", "last_updated", "tags"],
    }

    if config["use_semantic"]:
        search_kwargs["query_type"] = QueryType.SEMANTIC
        search_kwargs["semantic_configuration_name"] = config["semantic_config"]
        # Get semantic captions for better grounding signals
        search_kwargs["query_caption"] = "extractive"
        search_kwargs["query_answer"] = "extractive"

    results = search_client.search(**search_kwargs)

    chunks = []
    for result in results:
        # Filter by minimum score
        score = result.get("@search.reranker_score") or result.get("@search.score", 0)
        if score < config["score_threshold"]:
            continue

        chunks.append({
            "id": result["id"],
            "document_name": result["document_name"],
            "document_type": result["document_type"],
            "heading": result.get("heading", ""),
            "text": result["text"],
            "page_number": result.get("page_number"),
            "score": round(score, 3),
            "caption": result.get("@search.captions", [None])[0]
        })

    return chunks
```

---

## 7. Context Window Construction

How you format retrieved chunks for Claude significantly affects accuracy and citation quality.

```python
def build_rag_context(
    chunks: list[dict],
    max_chunks: int = 6,
    max_chars_per_chunk: int = 800,
    include_scores: bool = False
) -> str:
    """
    Format retrieved chunks as numbered, sourced passages for Claude.

    The [N] numbering allows Claude to generate [Source: N] citations
    that can be traced back to specific documents.

    Args:
        chunks: Retrieved and ranked chunks
        max_chunks: Maximum chunks to include (higher = more context, more tokens)
        max_chars_per_chunk: Truncate long chunks (prevents context bloat)
        include_scores: Include relevance scores (useful for debugging)

    Returns:
        Formatted context string for insertion into system prompt

    Example output:
        [1] Source: wine_list_2026.pdf (wine_list), p.8
        Château Léoville-Barton 2018, Saint-Julien — Structured tannins...
        ---
        [2] Source: wine_list_2026.pdf (wine_list), p.12
        Barolo Serralunga d'Alba 2019 — Tar, roses, cherries...
    """
    if not chunks:
        return "No relevant information found in the knowledge base."

    parts = []
    for i, chunk in enumerate(chunks[:max_chunks], 1):
        # Truncate if needed
        text = chunk["text"]
        if len(text) > max_chars_per_chunk:
            text = text[:max_chars_per_chunk] + "..."

        # Build source citation line
        source_parts = [f"Source: {chunk['document_name']} ({chunk['document_type']})"]
        if chunk.get("heading"):
            source_parts.append(f"§ {chunk['heading']}")
        if chunk.get("page_number") and chunk["page_number"] > 0:
            source_parts.append(f"p.{chunk['page_number']}")
        if include_scores:
            source_parts.append(f"score: {chunk['score']}")

        source_line = ", ".join(source_parts)

        parts.append(f"[{i}] {source_line}\n{text}")

    return "\n---\n".join(parts)

def estimate_context_tokens(context: str) -> int:
    """Rough token estimate: ~0.75 tokens per word."""
    return int(len(context.split()) / 0.75)
```

---

## 8. RAG System Prompt Design

The RAG system prompt is critical for grounding and citation quality.

```python
RAG_SYSTEM_PROMPT = """
You are Maître, the AI concierge for Lumière restaurant.

GROUNDING RULES (always follow):
1. Answer questions ONLY using information from the <context> section below.
2. If the answer is not in the context, say exactly:
   "I don't have that information in our current records. Please ask a team member directly."
3. Never fabricate prices, wine vintages, ingredients, or policies.
4. Every factual claim must be followed by [Source: document_name] or [N] (matching context numbers).
5. If the context contains conflicting information, present both versions and note the conflict.

CITATION FORMAT:
- For wine recommendations: cite as [wine_list_2026.pdf]
- For menu items: cite as [menu_spring_2026.pdf]
- For policies: cite as [policy_handbook.pdf]
- For multiple sources: [1, 3] (matching context numbers)

CONFIDENCE SIGNALS:
- High confidence: Information directly stated in context → answer fully
- Medium confidence: Information implied but not explicit → answer with "Based on..."
- Low confidence: Would require inference → use the fallback phrase above

ALLERGEN SPECIAL RULE:
If ANY allergen is discussed, ALWAYS append:
"Please confirm allergen details directly with your server before ordering."
This rule overrides all other instructions.
"""

def build_full_rag_prompt(
    base_persona: str,
    context: str
) -> list[dict]:
    """
    Build the full system prompt with cached persona + dynamic context.
    The persona is cached; context changes per query so is not cached.
    """
    return [
        # Block 1: Cached persona (stable — pays 0.10× on cache hits)
        {
            "type": "text",
            "text": base_persona,
            "cache_control": {"type": "ephemeral"}
        },
        # Block 2: Dynamic retrieved context (NOT cached — changes per query)
        {
            "type": "text",
            "text": f"<context>\n{context}\n</context>"
        }
    ]
```

---

## 9. Groundedness Evaluation

Measure how well Claude's response is grounded in the provided context. Run this in production for monitoring.

```python
GROUNDEDNESS_JUDGE_PROMPT = """
Evaluate whether the AI response is grounded in the provided context.

Scoring:
1.0 = All claims in the response are directly stated in the context
0.8 = Almost all claims grounded; one or two minor additions
0.6 = Most claims grounded; some unsupported additions
0.4 = Mixed: some grounded claims, some hallucinations
0.2 = Mostly hallucinated; few claims from context
0.0 = Entirely hallucinated; nothing from context

Return ONLY valid JSON:
{
  "groundedness_score": 0.0-1.0,
  "ungrounded_claims": ["claim1 that is not in context", ...],
  "missing_citations": ["fact stated without citation"],
  "verdict": "grounded" | "partially_grounded" | "hallucinated"
}

<context>
{context}
</context>

<response>
{response}
</response>
"""

def evaluate_groundedness(
    context: str,
    response: str,
    judge_model: str = "claude-sonnet-4-6"  # Use a strong judge model
) -> dict:
    """
    Evaluate groundedness of a RAG response using LLM-as-judge.

    Args:
        context: The retrieved context chunks that were given to Claude
        response: Claude's generated response
        judge_model: Model to use as judge (should differ from generator)

    Returns:
        {
            "groundedness_score": float (0.0-1.0),
            "ungrounded_claims": list[str],
            "missing_citations": list[str],
            "verdict": str
        }
    """
    judge_response = client.messages.create(
        model=judge_model,
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": GROUNDEDNESS_JUDGE_PROMPT.format(
                context=context[:3000],  # Truncate for judge's context
                response=response
            )
        }]
    )

    try:
        result = parse_claude_json(judge_response.content[0].text)
        return result
    except Exception:
        return {"groundedness_score": 0.5, "verdict": "evaluation_failed"}

# Production monitoring: alert when groundedness drops below threshold
GROUNDEDNESS_ALERT_THRESHOLD = 0.80

def monitor_groundedness(response: str, context: str, session_id: str):
    """Log groundedness score; alert if below threshold."""
    score_data = evaluate_groundedness(context, response)
    score = score_data.get("groundedness_score", 0)

    logger.info(
        "groundedness_evaluated",
        session_id=session_id,
        score=score,
        verdict=score_data.get("verdict"),
        ungrounded_claims=score_data.get("ungrounded_claims", [])
    )

    if score < GROUNDEDNESS_ALERT_THRESHOLD:
        logger.warning(
            "groundedness_below_threshold",
            session_id=session_id,
            score=score,
            claims=score_data.get("ungrounded_claims")
        )
```

---

## 10. Advanced RAG Patterns

### HyDE — Hypothetical Document Embeddings

Instead of embedding the query, generate a hypothetical answer and embed that. Improves recall for short queries.

```python
def hyde_retrieve(
    query: str,
    search_engine,
    model: str = "claude-haiku-4-5-20251001"
) -> list[dict]:
    """
    HyDE: Generate a hypothetical answer to the query, then use ITS
    embedding for retrieval. Improves recall for vague queries.

    Standard approach: embed("red wine for lamb") → retrieve
    HyDE approach:     embed(hypothetical_answer) → retrieve
    """
    # Generate a hypothetical answer
    hypo_response = client.messages.create(
        model=model,
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": (
                f"Write a brief, factual answer to this question as if you were "
                f"a restaurant expert with access to a wine list:\n\n{query}"
            )
        }]
    )
    hypothetical_answer = hypo_response.content[0].text

    # Embed the hypothetical answer (not the original query)
    embedding = generate_embeddings_batch([hypothetical_answer])[0]

    # Retrieve based on hypothetical answer embedding
    return search_engine.search(hypothetical_answer, embedding)
```

### Multi-Query Retrieval

Run multiple query variations and merge results for better recall.

```python
def multi_query_retrieve(
    query: str,
    search_engine,
    top_k_per_query: int = 4
) -> list[dict]:
    """
    Generate multiple query variations and merge results.
    Improves recall especially for ambiguous or short queries.
    """
    query_data = analyse_and_rewrite_query(query)
    all_queries = [query_data["primary_query"]] + query_data.get("secondary_queries", [])

    all_chunks = {}  # Deduplicate by chunk ID

    for q in all_queries[:3]:  # Limit to 3 queries to control cost
        embedding = generate_embeddings_batch([q])[0]
        chunks = search_engine.search(q, embedding, top_k=top_k_per_query)

        for chunk in chunks:
            # Keep highest-scoring version if chunk appears in multiple queries
            if chunk["id"] not in all_chunks or chunk["score"] > all_chunks[chunk["id"]]["score"]:
                all_chunks[chunk["id"]] = chunk

    # Sort by score and return top results
    merged = sorted(all_chunks.values(), key=lambda x: x["score"], reverse=True)
    return merged[:top_k_per_query * 2]  # Return more than single query would
```

---

## 11. Junior Quick-Start Walkthrough

**Goal**: Build a basic RAG Q&A system in 30 minutes.

**Step 1**: Prepare a document as chunks.

```python
# Simple approach: chunk a text file
with open("wine_list.txt") as f:
    text = f.read()

# Chunk it (simple fixed-window)
words = text.split()
chunk_size = 200  # words per chunk
chunks = []
for i in range(0, len(words), chunk_size - 20):  # 20-word overlap
    chunks.append(" ".join(words[i:i+chunk_size]))
print(f"Created {len(chunks)} chunks")
```

**Step 2**: Store chunks in memory (skip Azure AI Search for dev).

```python
# For development: use in-memory storage
knowledge_base = chunks  # Just a list of strings
```

**Step 3**: Retrieve by simple keyword match (upgrade to vector search in production).

```python
def simple_retrieve(question: str, chunks: list[str], top_k: int = 3) -> list[str]:
    """Simple keyword matching — good enough for development/testing."""
    keywords = question.lower().split()
    scored = []
    for chunk in chunks:
        chunk_lower = chunk.lower()
        score = sum(1 for kw in keywords if kw in chunk_lower)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(reverse=True)
    return [chunk for _, chunk in scored[:top_k]]
```

**Step 4**: Build the RAG prompt and generate.

```python
def rag_answer(question: str) -> str:
    # Retrieve relevant chunks
    relevant_chunks = simple_retrieve(question, knowledge_base)

    # Format context
    context = "\n---\n".join(f"[{i+1}] {chunk}" for i, chunk in enumerate(relevant_chunks))

    # Generate grounded answer
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=f"""Answer using ONLY this context:
<context>
{context}
</context>
If not in context, say 'I don't have that information.'
Always cite [N] matching the context numbers.""",
        messages=[{"role": "user", "content": question}]
    )

    return response.content[0].text

# Test
print(rag_answer("What red wines do you have?"))
```

---

## 12. Senior Patterns and Production Hardening

### Index Freshness Management

```python
class IndexFreshnessManager:
    """
    Track and enforce freshness of indexed documents.
    Alert when documents are outdated (e.g., wine list is 30 days old).
    """

    FRESHNESS_LIMITS = {
        "wine_list": timedelta(days=30),      # Monthly updates
        "menu": timedelta(days=7),            # Weekly seasonal updates
        "policy": timedelta(days=90),         # Quarterly reviews
        "allergen_guide": timedelta(days=14), # Bi-weekly safety-critical updates
        "faq": timedelta(days=60),
    }

    def check_staleness(self, search_client) -> list[dict]:
        """Check all indexed documents for staleness."""
        stale = []
        for doc_type, max_age in self.FRESHNESS_LIMITS.items():
            # Query for most recent document of each type
            results = search_client.search(
                search_text="*",
                filter=f"document_type eq '{doc_type}'",
                top=1,
                order_by=["last_updated desc"],
                select=["document_name", "last_updated"]
            )
            for doc in results:
                updated = datetime.fromisoformat(doc["last_updated"])
                age = datetime.utcnow() - updated
                if age > max_age:
                    stale.append({
                        "document_type": doc_type,
                        "document_name": doc["document_name"],
                        "age_days": age.days,
                        "max_age_days": max_age.days
                    })
        return stale
```

---

## 13. Tips, Tricks and Gotchas

**Tip 1 — Chunk size matters more than most RAG practitioners realise.** For structured content like wine lists, one item per chunk (150 tokens) dramatically outperforms 500-token sliding windows. Match chunk size to the semantic unit.

**Tip 2 — Over-retrieve and re-rank.** Request 3× the final top_k from the vector search, then let the semantic ranker select the best. This significantly improves precision.

**Tip 3 — Always include the source in each chunk at index time.** Add `Source: document_name, p.X` as metadata — don't just store the text. Claude needs this for accurate citation.

**Tip 4 — Monitor zero-result queries.** When no chunks pass the score threshold, Claude falls back to its training data. Log these queries and use them to identify gaps in your knowledge base.

**Tip 5 — Use HyDE for conversational or vague queries.** Short, conversational queries ("what reds do you have?") retrieve better when you embed a hypothetical answer rather than the raw query.

**Gotcha 1 — Hybrid search is not automatic.** Azure AI Search needs both `search_text=` (for BM25) AND `vector_queries=` (for semantic) to do true hybrid search. Passing only vector_queries gives you pure vector search.

**Gotcha 2 — Semantic ranker requires Standard tier or higher.** If you're on Basic tier, `query_type=SEMANTIC` fails silently or raises an error. Check your tier.

**Gotcha 3 — Chunk overlap is critical at document boundaries.** A wine that spans a chunk boundary without overlap may be split into "Château Léo..." and "...ville-Barton 2018 £145". Use overlap that covers at least one complete entry.

**Gotcha 4 — Cached system prompt + dynamic context = right order.** The cached persona block must come BEFORE the context block. If you put the dynamic context first, the cache is invalidated and you pay full price.

**Gotcha 5 — LLM judges are biased toward their own output style.** Never use the same model as both generator and judge. If your system uses Sonnet 4.6, use Opus or GPT-4o as the judge.

---

## 14. Quick Reference Cheatsheet

```
RAG PIPELINE STEPS:
  Index: Document → Chunk → Embed → Upload to Azure AI Search
  Query: Query → Rewrite → Embed → Hybrid Search → Format → Generate → Evaluate

CHUNK SIZE GUIDE:
  Wine/menu items:  100-200 tokens (one item = one chunk)
  Prose sections:   400-600 tokens (semantic unit)
  General text:     500 tokens + 50 overlap

SEARCH TYPE COMPARISON:
  Keyword (BM25):  Exact term match — good for product names, codes
  Vector:          Semantic similarity — good for meaning
  Hybrid:          Both combined — best for general RAG
  Semantic ranker: Neural re-ranking of top results — highest precision

TOP_K GUIDELINES:
  Simple factual:      3 chunks
  Comparative query:   5 chunks
  Safety (allergens):  8 chunks (over-retrieve to be safe)

GROUNDING PROMPT TEMPLATE:
  "Answer ONLY from <context>. Cite as [N]. If not in context:
   'I don't have that information.'"

GROUNDEDNESS THRESHOLDS:
  Production minimum:  0.80
  Safety-critical:     0.95 (allergens, medical)
  Alert threshold:     Drop > 5% from baseline

COMMON PITFALLS:
  ✗ One chunk size for all document types
  ✗ Vector-only search (use hybrid)
  ✗ No citations in system prompt
  ✗ Same model as judge and generator
  ✗ Uncached persona block (costs 10× more)
  ✗ Not monitoring zero-result queries
```
