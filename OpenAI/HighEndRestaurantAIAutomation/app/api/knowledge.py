from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas_episode5 import (
    ContentUnderstandingResponse,
    DocumentExtractionResponse,
    SearchIngestStatusResponse,
    SearchQueryRequest,
    SearchQueryResponse,
)
from app.schemas_episode6 import (
    AnalyzerDefinitionResponse,
    ContentUnderstandingResponse as ContentUnderstandingResponseV2,
    ExtractionResultV2,
    IngestionJobResponse,
    IngestionStatusResponse,
    ReviewCorrectionRequest,
    ReviewDecisionRequest,
    ReviewItem,
    SearchQueryRequestV2,
    SearchQueryResponseV2,
)
from app.ingestion.pipeline import knowledge_ingestion_pipeline
from app.review.human_review_queue import human_review_queue
from app.services.content_understanding_client import ContentUnderstandingClient
from app.services.document_intelligence_client import DocumentIntelligenceClient
from app.services.search_client import RestaurantSearchClient

router = APIRouter(tags=["episode5-knowledge-mining"])

search_client = RestaurantSearchClient()
document_client = DocumentIntelligenceClient()
content_understanding_client = ContentUnderstandingClient()


@router.post("/search/query", response_model=SearchQueryResponse)
async def search_query(request: SearchQueryRequest):
    result = await search_client.search_knowledge(
        request.query,
        query_type=request.query_type,
        top_k=request.top_k,
        document_type=request.document_type,
        menu_section=request.menu_section,
        allergen_tag=request.allergen_tag,
        require_citations=request.require_citations,
    )
    return SearchQueryResponse(**result)


@router.post("/search/query/v2", response_model=SearchQueryResponseV2)
async def search_query_v2(request: SearchQueryRequestV2):
    result = await search_client.search_knowledge(
        request.query,
        query_type=request.query_type,
        top_k=request.top_k,
        document_type=request.document_type,
        category=request.category,
        language=request.language,
        access_level=request.access_level,
        menu_section=request.menu_section,
        allergen_tag=request.allergen_tag,
        include_facets=request.include_facets,
        use_zero_result_fallback=request.use_zero_result_fallback,
        require_citations=request.require_citations,
    )
    return SearchQueryResponseV2(**result)


@router.get("/search/ingest-status", response_model=SearchIngestStatusResponse)
async def search_ingest_status():
    return SearchIngestStatusResponse(**(await search_client.get_ingest_status()))


@router.get("/search/query-log")
async def search_query_log():
    return {"queries": await search_client.get_query_logs()}


@router.post("/document/receipt", response_model=DocumentExtractionResponse)
async def analyze_receipt(file: UploadFile = File(...)):
    return DocumentExtractionResponse(**(await document_client.analyze_receipt(await file.read())))


@router.post("/document/receipt/v2", response_model=ExtractionResultV2)
async def analyze_receipt_v2(file: UploadFile = File(...)):
    return ExtractionResultV2(**(await document_client.analyze_receipt(await file.read())))


@router.post("/document/layout", response_model=DocumentExtractionResponse)
async def analyze_layout(file: UploadFile = File(...)):
    return DocumentExtractionResponse(**(await document_client.analyze_layout(await file.read())))


@router.post("/document/layout/v2", response_model=ExtractionResultV2)
async def analyze_layout_v2(file: UploadFile = File(...)):
    return ExtractionResultV2(**(await document_client.analyze_layout(await file.read())))


@router.post("/document/contract", response_model=DocumentExtractionResponse)
async def analyze_contract(file: UploadFile = File(...)):
    return DocumentExtractionResponse(**(await document_client.analyze_custom_event_document(await file.read())))


@router.post("/document/contract/v2", response_model=ExtractionResultV2)
async def analyze_contract_v2(file: UploadFile = File(...)):
    return ExtractionResultV2(**(await document_client.analyze_custom_event_document(await file.read())))


@router.post("/content-understanding/analyze", response_model=ContentUnderstandingResponse)
async def analyze_content_understanding(
    analyzer_id: str = Form(...),
    file: UploadFile = File(...),
):
    result = await content_understanding_client.analyze_content(
        analyzer_id=analyzer_id,
        content_bytes=await file.read(),
        filename=file.filename,
        content_type=file.content_type,
    )
    return ContentUnderstandingResponse(**result)


@router.post("/content-understanding/analyze/v2", response_model=ContentUnderstandingResponseV2)
async def analyze_content_understanding_v2(
    analyzer_id: str = Form(...),
    file: UploadFile = File(...),
):
    result = await content_understanding_client.analyze_content(
        analyzer_id=analyzer_id,
        content_bytes=await file.read(),
        filename=file.filename,
        content_type=file.content_type,
    )
    return ContentUnderstandingResponseV2(**result)


@router.get("/content-understanding/analyzers", response_model=list[AnalyzerDefinitionResponse])
async def list_content_understanding_analyzers():
    return [AnalyzerDefinitionResponse(**item) for item in content_understanding_client.list_analyzers()]


@router.post("/ingestion/jobs", response_model=IngestionJobResponse)
async def create_ingestion_job(file: UploadFile = File(...)):
    job = await knowledge_ingestion_pipeline.ingest(
        filename=file.filename or "upload.bin",
        content_bytes=await file.read(),
        content_type=file.content_type,
    )
    return IngestionJobResponse(**job)


@router.get("/ingestion/jobs", response_model=IngestionStatusResponse)
async def list_ingestion_jobs():
    return IngestionStatusResponse(jobs=[IngestionJobResponse(**job) for job in knowledge_ingestion_pipeline.list_jobs()])


@router.get("/ingestion/jobs/{job_id}", response_model=IngestionJobResponse)
async def get_ingestion_job(job_id: str):
    job = knowledge_ingestion_pipeline.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    return IngestionJobResponse(**job)


@router.get("/reviews", response_model=list[ReviewItem])
async def list_reviews(status: str | None = None):
    return [ReviewItem(**item) for item in human_review_queue.list(status=status)]


@router.post("/reviews/{review_id}/approve", response_model=ReviewItem)
async def approve_review(review_id: str, request: ReviewDecisionRequest):
    item = human_review_queue.get(review_id)
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")
    return ReviewItem(**human_review_queue.approve(review_id, actor=request.actor, notes=request.notes))


@router.post("/reviews/{review_id}/reject", response_model=ReviewItem)
async def reject_review(review_id: str, request: ReviewDecisionRequest):
    item = human_review_queue.get(review_id)
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")
    return ReviewItem(**human_review_queue.reject(review_id, actor=request.actor, notes=request.notes))


@router.post("/reviews/{review_id}/correct", response_model=ReviewItem)
async def correct_review(review_id: str, request: ReviewCorrectionRequest):
    item = human_review_queue.get(review_id)
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")
    return ReviewItem(**human_review_queue.correct(review_id, actor=request.actor, corrections=request.corrections, notes=request.notes))
