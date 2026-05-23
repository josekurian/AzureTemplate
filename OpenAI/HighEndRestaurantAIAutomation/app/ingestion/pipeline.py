from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

from app.ingestion.chunking import chunk_markdown
from app.ingestion.embedder import RestaurantEmbedder
from app.ingestion.normalizers import (
    normalize_content_understanding_result,
    normalize_document_intelligence_result,
)
from app.review.human_review_queue import human_review_queue
from app.services.content_understanding_client import ContentUnderstandingClient
from app.services.document_intelligence_client import DocumentIntelligenceClient
from app.services.search_client import RestaurantSearchClient


class KnowledgeIngestionPipeline:
    def __init__(self) -> None:
        self._document_client = DocumentIntelligenceClient()
        self._content_client = ContentUnderstandingClient()
        self._search_client = RestaurantSearchClient()
        self._embedder = RestaurantEmbedder()
        self._jobs: dict[str, dict] = {}

    @staticmethod
    def _infer_route(filename: str, content_type: str | None) -> tuple[str, str]:
        lowered = filename.lower()
        media_type = (content_type or "").lower()
        if "invoice" in lowered:
            return "document_intelligence", "invoice"
        if "receipt" in lowered:
            return "document_intelligence", "receipt"
        if "contract" in lowered or "private" in lowered:
            return "document_intelligence", "custom_event_contract"
        if lowered.endswith(".wav") or lowered.endswith(".mp3") or media_type.startswith("audio/"):
            return "content_understanding", "guest_call_audio"
        if lowered.endswith(".mp4") or media_type.startswith("video/"):
            return "content_understanding", "chef_video"
        if "menu" in lowered:
            return "content_understanding", "menu_pdf"
        return "content_understanding", "supplier_invoice_review"

    async def ingest(
        self,
        *,
        filename: str,
        content_bytes: bytes,
        content_type: str | None,
    ) -> dict:
        job_id = f"ingest-{uuid4()}"
        correlation_id = str(uuid4())
        route, analyzer_or_doc_type = self._infer_route(filename, content_type)

        if route == "document_intelligence":
            if analyzer_or_doc_type == "invoice":
                raw_result = await self._document_client.analyze_invoice(content_bytes)
            elif analyzer_or_doc_type == "receipt":
                raw_result = await self._document_client.analyze_receipt(content_bytes)
            else:
                raw_result = await self._document_client.analyze_custom_event_document(content_bytes)
            normalized = normalize_document_intelligence_result(raw_result, source=filename)
        else:
            raw_result = await self._content_client.analyze_content(
                analyzer_id=analyzer_or_doc_type,
                content_bytes=content_bytes,
                filename=filename,
                content_type=content_type,
            )
            normalized = normalize_content_understanding_result(raw_result, source=filename)

        chunks = chunk_markdown(
            normalized["content_markdown"],
            source_id=filename.replace(".", "-"),
            metadata={
                "title": normalized["title"],
                "source": normalized["source"],
                "document_type": normalized["document_type"],
                "category": normalized["category"],
                "language": normalized["language"],
                "access_level": normalized["access_level"],
                "page": normalized["page"],
                "section": normalized["section"],
                "effective_date": normalized["effective_date"],
                "confidence": normalized["confidence"],
                "grounding": normalized["grounding"],
                "allergen_tags": normalized["allergen_tags"],
                "menu_section": normalized["menu_section"],
                "metadata_json": normalized["metadata_json"],
            },
        )

        indexed_document_ids: list[str] = []
        review_id = None
        warnings = list(raw_result.get("warnings", []))
        status = "completed"
        if normalized["human_review_required"] or normalized["confidence"] < 0.9:
            review = human_review_queue.create(
                source=filename,
                document_type=normalized["document_type"],
                confidence=normalized["confidence"],
                reason="low_confidence_extraction",
                payload={"normalized": normalized, "raw_result": raw_result, "chunks": chunks},
            )
            review_id = review["review_id"]
            status = "review_required"
            warnings.append("Document was routed to human review before indexing.")
        else:
            index_documents = []
            for chunk in chunks:
                vector = await self._embedder.embed_text(chunk["content"])
                index_documents.append(
                    {
                        "id": chunk["id"],
                        "chunk_id": chunk["chunk_id"],
                        "title": normalized["title"],
                        "source": normalized["source"],
                        "content": chunk["content"],
                        "content_vector": vector,
                        "document_type": normalized["document_type"],
                        "category": normalized["category"],
                        "language": normalized["language"],
                        "access_level": normalized["access_level"],
                        "page": normalized["page"],
                        "section": chunk.get("section"),
                        "effective_date": normalized["effective_date"],
                        "confidence": normalized["confidence"],
                        "grounding": normalized["grounding"],
                        "allergen_tags": normalized["allergen_tags"],
                        "menu_section": normalized["menu_section"],
                        "metadata_json": normalized["metadata_json"],
                    }
                )
            await self._search_client.publish_documents(index_documents)
            indexed_document_ids = [item["id"] for item in index_documents]

        job = {
            "job_id": job_id,
            "status": status,
            "route": route,
            "filename": filename,
            "document_type": normalized["document_type"],
            "confidence": normalized["confidence"],
            "review_id": review_id,
            "indexed_document_ids": indexed_document_ids,
            "correlation_id": correlation_id,
            "warnings": warnings,
        }
        self._jobs[job_id] = job
        return deepcopy(job)

    def list_jobs(self) -> list[dict]:
        return [deepcopy(job) for job in self._jobs.values()]

    def get_job(self, job_id: str) -> dict | None:
        job = self._jobs.get(job_id)
        return deepcopy(job) if job else None


knowledge_ingestion_pipeline = KnowledgeIngestionPipeline()
