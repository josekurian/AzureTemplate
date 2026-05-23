from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class SearchQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Guest or staff search query")
    query_type: Literal["keyword", "vector", "hybrid", "semantic"] = "hybrid"
    top_k: int = Field(5, ge=1, le=10)
    document_type: Optional[str] = Field(default=None, description="Optional filter such as menu, policy, faq, contract")
    menu_section: Optional[str] = None
    allergen_tag: Optional[str] = None
    require_citations: bool = True


class SearchCitation(BaseModel):
    source: str
    title: str
    chunk_id: str
    page_number: Optional[int] = None
    excerpt: str


class SearchResult(BaseModel):
    id: str
    title: str
    source: str
    content: str
    document_type: str
    score: float
    reranker_score: Optional[float] = None
    page_number: Optional[int] = None
    chunk_id: str
    menu_section: Optional[str] = None
    allergen_tags: list[str] = Field(default_factory=list)


class SearchDiagnostics(BaseModel):
    query_type: str
    applied_filters: dict[str, Any] = Field(default_factory=dict)
    result_count: int
    used_vector_search: bool
    used_semantic_ranker: bool
    embedding_dimensions: int


class SearchQueryResponse(BaseModel):
    context: str
    sources: list[str] = Field(default_factory=list)
    citations: list[SearchCitation] = Field(default_factory=list)
    results: list[SearchResult] = Field(default_factory=list)
    diagnostics: SearchDiagnostics


class SearchIngestStatusResponse(BaseModel):
    status: str
    index_name: str
    document_count: int
    indexed_sources: list[str] = Field(default_factory=list)
    last_sync_hint: str


class DocumentExtractionResponse(BaseModel):
    document_type: str
    summary: str
    confidence: float
    human_review_required: bool
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    line_items: list[dict[str, Any]] = Field(default_factory=list)
    paragraphs: list[str] = Field(default_factory=list)
    tables: list[dict[str, Any]] = Field(default_factory=list)


class ContentUnderstandingResponse(BaseModel):
    analyzer_id: str
    status: str
    summary: str
    fields: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
