"""
document_ingestion.py — Phase 3: Ingest restaurant documents into AI Search
==========================================================================
AI-102 Skills:
  Phase 3 — Document Intelligence: extract structured fields from PDFs
  Phase 4 — AI Search: push enriched chunks + embeddings into the index

Restaurant documents handled:
  - Wine list PDFs       → extract vintage, producer, appellation, price
  - Tasting menus        → extract dish names, allergens, course structure
  - Supplier invoices    → extract vendor, items, unit costs (prebuilt invoice model)
  - Staff training docs  → extract policy text for knowledge base Q&A
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Optional

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI

from src.config import RestaurantAIConfig, get_credential
from src.monitoring.telemetry import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class DocumentIngestionPipeline:
    """
    End-to-end ingestion pipeline:
      Blob Storage PDF → Document Intelligence → Chunk → Embed → AI Search Index
    """

    def __init__(self, config: RestaurantAIConfig):
        self.config = config
        credential = get_credential()

        # Document Intelligence client (keyless via Managed Identity)
        self.doc_client = DocumentIntelligenceClient(
            endpoint=config.doc_intelligence_endpoint,
            credential=credential,
        )

        # AI Search client (index writer)
        self.search_client = SearchClient(
            endpoint=config.search_endpoint,
            index_name=config.search_index_name,
            credential=credential,
        )

        # Blob Storage client
        account_url = f"https://{config.storage_account_name}.blob.core.windows.net"
        self.blob_service = BlobServiceClient(account_url=account_url, credential=credential)

        # Azure OpenAI client for embeddings (keyless)
        self.openai_client = AzureOpenAI(
            azure_endpoint=config.openai_endpoint,
            azure_ad_token_provider=lambda: credential.get_token(
                "https://cognitiveservices.azure.com/.default"
            ).token,
            api_version=config.openai_api_version,
        )

    def ingest_blob_container(self, container_name: Optional[str] = None) -> dict:
        """
        List all PDFs in the blob container and ingest each one.
        Returns a summary of processed / skipped / failed documents.
        """
        container = container_name or self.config.storage_container_name
        container_client = self.blob_service.get_container_client(container)

        stats = {"processed": 0, "skipped": 0, "failed": 0}
        for blob in container_client.list_blobs():
            if not blob.name.lower().endswith(".pdf"):
                stats["skipped"] += 1
                continue
            try:
                logger.info(f"Processing blob: {blob.name}")
                blob_url = f"https://{self.config.storage_account_name}.blob.core.windows.net/{container}/{blob.name}"
                self._process_document(blob_url=blob_url, document_name=blob.name)
                stats["processed"] += 1
            except Exception as exc:
                logger.error(f"Failed to process {blob.name}: {exc}", exc_info=True)
                stats["failed"] += 1

        logger.info(f"Ingestion complete: {stats}")
        return stats

    def _process_document(self, blob_url: str, document_name: str) -> None:
        """
        Full pipeline for a single document:
          1. Document Intelligence → layout + key-value extraction
          2. Chunk the content into ~500 token passages
          3. Generate embeddings for each chunk
          4. Upsert chunks into AI Search index
        """
        with tracer.start_as_current_span("document_ingestion") as span:
            span.set_attribute("document.name", document_name)

            # ── Step 1: Document Intelligence extraction ──────────────────────
            logger.info(f"Running Document Intelligence on: {document_name}")

            # Choose model based on document type
            # AI-102: prebuilt-invoice for supplier docs, prebuilt-layout for menus/wine lists
            model_id = self._select_model(document_name)

            poller = self.doc_client.begin_analyze_document(
                model_id=model_id,
                analyze_request=AnalyzeDocumentRequest(url_source=blob_url),
            )
            result = poller.result()

            # ── Step 2: Extract text and metadata ────────────────────────────
            extracted = self._extract_content(result, document_name)

            # ── Step 3: Chunk and embed ───────────────────────────────────────
            chunks = self._chunk_content(extracted["full_text"], window=500, overlap=50)
            logger.info(f"Generated {len(chunks)} chunks from {document_name}")

            documents_to_index = []
            for i, chunk_text in enumerate(chunks):
                doc_id = hashlib.md5(f"{document_name}_{i}".encode()).hexdigest()
                embedding = self._generate_embedding(chunk_text)

                documents_to_index.append({
                    "id": doc_id,
                    "document_name": document_name,
                    "chunk_index": i,
                    "content": chunk_text,
                    "content_vector": embedding,          # For vector/hybrid search
                    "document_type": extracted["doc_type"],
                    "metadata_json": json.dumps(extracted.get("fields", {})),
                    "page_count": extracted.get("page_count", 1),
                    "blob_url": blob_url,
                })

            # ── Step 4: Upsert into AI Search ─────────────────────────────────
            if documents_to_index:
                result_upload = self.search_client.upload_documents(documents=documents_to_index)
                span.set_attribute("chunks.indexed", len(documents_to_index))
                logger.info(f"Indexed {len(documents_to_index)} chunks for {document_name}")

    def _select_model(self, document_name: str) -> str:
        """
        AI-102: Pre-built models require no training.
        invoice → supplier purchase orders
        receipt → expense receipts
        layout  → menus, wine lists, training documents
        """
        name_lower = document_name.lower()
        if any(kw in name_lower for kw in ["invoice", "supplier", "purchase_order"]):
            return "prebuilt-invoice"
        elif any(kw in name_lower for kw in ["receipt", "expense"]):
            return "prebuilt-receipt"
        else:
            return "prebuilt-layout"  # Best for menus, wine lists, policy docs

    def _extract_content(self, result, document_name: str) -> dict:
        """Extract full text and typed fields from Document Intelligence result."""
        full_text_parts = []
        fields = {}

        # Extract text from all pages
        for page in result.pages or []:
            for line in page.lines or []:
                full_text_parts.append(line.content)

        # Extract key-value pairs (prebuilt-invoice fields)
        if result.documents:
            for doc in result.documents:
                for field_name, field_value in (doc.fields or {}).items():
                    if field_value and field_value.content:
                        fields[field_name] = field_value.content

        # Classify document type for metadata
        doc_type = "general"
        name_lower = document_name.lower()
        if "wine" in name_lower:
            doc_type = "wine_list"
        elif "menu" in name_lower:
            doc_type = "menu"
        elif "invoice" in name_lower or "supplier" in name_lower:
            doc_type = "supplier_invoice"
        elif "training" in name_lower or "policy" in name_lower:
            doc_type = "staff_training"

        return {
            "full_text": "\n".join(full_text_parts),
            "fields": fields,
            "doc_type": doc_type,
            "page_count": len(result.pages or []),
        }

    def _chunk_content(self, text: str, window: int = 500, overlap: int = 50) -> list[str]:
        """
        Simple word-boundary chunking with overlap.
        AI-102: Overlap preserves context across chunk boundaries for RAG retrieval.
        """
        words = text.split()
        if not words:
            return []
        chunks = []
        start = 0
        while start < len(words):
            end = min(start + window, len(words))
            chunks.append(" ".join(words[start:end]))
            start += window - overlap
        return chunks

    def _generate_embedding(self, text: str) -> list[float]:
        """
        Generate text embedding using Azure OpenAI text-embedding-3-large.
        AI-102: Embedding deployment name is separate from the model family name.
        """
        response = self.openai_client.embeddings.create(
            input=text,
            model=self.config.openai_embedding_deployment,  # deployment name, not model name
        )
        return response.data[0].embedding
