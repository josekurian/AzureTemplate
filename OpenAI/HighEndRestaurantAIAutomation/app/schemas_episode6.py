from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class GroundingReference(BaseModel):
    source: str
    title: str
    chunk_id: str
    page: Optional[int] = None
    section: Optional[str] = None
    confidence: float = 0.0
    excerpt: str


class SearchFacetBucket(BaseModel):
    value: str
    count: int


class SearchFacetSet(BaseModel):
    document_type: list[SearchFacetBucket] = Field(default_factory=list)
    category: list[SearchFacetBucket] = Field(default_factory=list)
    language: list[SearchFacetBucket] = Field(default_factory=list)


class SearchQueryRequestV2(BaseModel):
    query: str = Field(..., min_length=2)
    query_type: Literal["keyword", "vector", "hybrid", "semantic"] = "hybrid"
    top_k: int = Field(5, ge=1, le=10)
    document_type: Optional[str] = None
    category: Optional[str] = None
    language: Optional[str] = None
    access_level: Optional[str] = "public"
    menu_section: Optional[str] = None
    allergen_tag: Optional[str] = None
    include_facets: bool = True
    use_zero_result_fallback: bool = True
    require_citations: bool = True


class SearchResultV2(BaseModel):
    id: str
    title: str
    source: str
    content: str
    document_type: str
    category: str = "restaurant_knowledge"
    language: str = "en"
    access_level: str = "public"
    score: float
    reranker_score: Optional[float] = None
    page: Optional[int] = None
    section: Optional[str] = None
    chunk_id: str
    menu_section: Optional[str] = None
    allergen_tags: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    metadata_json: str = "{}"


class SearchDiagnosticsV2(BaseModel):
    query_type: str
    applied_filters: dict[str, Any] = Field(default_factory=dict)
    result_count: int
    used_vector_search: bool
    used_semantic_ranker: bool
    embedding_dimensions: int
    zero_result_fallback_used: bool = False
    correlation_id: Optional[str] = None


class SearchQueryResponseV2(BaseModel):
    context: str
    sources: list[str] = Field(default_factory=list)
    citations: list[GroundingReference] = Field(default_factory=list)
    results: list[SearchResultV2] = Field(default_factory=list)
    diagnostics: SearchDiagnosticsV2
    facets: SearchFacetSet = Field(default_factory=SearchFacetSet)


class ExtractionFieldConfidence(BaseModel):
    field_name: str
    confidence: float
    value: Any = None


class ExtractionResultV2(BaseModel):
    document_type: str
    summary: str
    confidence: float
    human_review_required: bool
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    line_items: list[dict[str, Any]] = Field(default_factory=list)
    paragraphs: list[str] = Field(default_factory=list)
    tables: list[dict[str, Any]] = Field(default_factory=list)
    field_confidences: list[ExtractionFieldConfidence] = Field(default_factory=list)
    markdown: str = ""
    grounding_references: list[GroundingReference] = Field(default_factory=list)


class ContentUnderstandingResponse(BaseModel):
    analyzer_id: str
    document_type: str
    status: str
    summary: str
    fields: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    markdown: str = ""
    grounding_references: list[GroundingReference] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    human_review_required: bool = False


class ReviewItem(BaseModel):
    review_id: str
    status: Literal["pending", "approved", "rejected", "corrected"]
    source: str
    document_type: str
    confidence: float
    reason: str
    payload: dict[str, Any] = Field(default_factory=dict)
    corrections: dict[str, Any] = Field(default_factory=dict)
    audit_log: list[dict[str, Any]] = Field(default_factory=list)


class ReviewDecisionRequest(BaseModel):
    actor: str
    notes: Optional[str] = None


class ReviewCorrectionRequest(ReviewDecisionRequest):
    corrections: dict[str, Any] = Field(default_factory=dict)


class IndexDocument(BaseModel):
    id: str
    chunk_id: str
    title: str
    source: str
    content: str
    content_vector: list[float] = Field(default_factory=list)
    document_type: str
    category: str
    language: str = "en"
    access_level: str = "public"
    page: Optional[int] = None
    section: Optional[str] = None
    effective_date: Optional[str] = None
    confidence: float = 1.0
    grounding: list[GroundingReference] = Field(default_factory=list)
    allergen_tags: list[str] = Field(default_factory=list)
    menu_section: Optional[str] = None
    metadata_json: str = "{}"


class IngestionJobResponse(BaseModel):
    job_id: str
    status: Literal["queued", "completed", "review_required", "failed"]
    route: str
    filename: str
    document_type: str
    confidence: float
    review_id: Optional[str] = None
    indexed_document_ids: list[str] = Field(default_factory=list)
    correlation_id: str
    warnings: list[str] = Field(default_factory=list)


class IngestionStatusResponse(BaseModel):
    jobs: list[IngestionJobResponse] = Field(default_factory=list)


class AnalyzerDefinitionResponse(BaseModel):
    analyzer_id: str
    name: str
    input_kinds: list[str] = Field(default_factory=list)
    targets: list[str] = Field(default_factory=list)
    default_options: dict[str, Any] = Field(default_factory=dict)
